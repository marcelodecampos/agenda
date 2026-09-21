"""Import IBGE municipalities and selected localities."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agenda.config import settings
from agenda.infrastructure.db import criar_engine


IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
LOCALIDADES_FONTE = "IBGE Cadastro de localidades selecionadas"


def _novo_id() -> str:
    return str(uuid.uuid7())


def importar_municipios(engine: object) -> int:
    response = httpx.get(IBGE_MUNICIPIOS_URL, timeout=60.0)
    response.raise_for_status()
    municipios = response.json()
    with engine.begin() as connection:
        ufs = {
            codigo: identificador
            for identificador, codigo in connection.execute(
                text("SELECT id, codigo_ibge FROM unidades_federacao")
            ).all()
        }
        if len(ufs) != 27:
            raise RuntimeError("as 27 UFs precisam existir antes da importação")
        for municipio in municipios:
            codigo = str(municipio["id"]).zfill(7)
            uf_id = ufs.get(codigo[:2])
            if uf_id is None:
                raise RuntimeError(f"UF IBGE {codigo[:2]} não encontrada para {codigo}")
            connection.execute(
                text(
                    "INSERT INTO municipios (id, codigo_ibge, nome, unidade_federacao_id) "
                    "VALUES (:id, :codigo, :nome, :uf_id) "
                    "ON CONFLICT (codigo_ibge) DO UPDATE SET nome = EXCLUDED.nome, "
                    "unidade_federacao_id = EXCLUDED.unidade_federacao_id"
                ),
                {
                    "id": _novo_id(),
                    "codigo": codigo,
                    "nome": municipio["nome"],
                    "uf_id": uf_id,
                },
            )
    return len(municipios)


def _executar_ogr(comando: list[str]) -> bytes:
    try:
        resultado = subprocess.run(comando, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"executável '{comando[0]}' não encontrado no PATH. Instale GDAL/OGR "
            "(por exemplo, GISInternals.GDAL) e reabra o terminal; depois confirme "
            "suporte a Access/GeoMedia com 'ogrinfo --formats'."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detalhe = exc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"OGR falhou: {detalhe}") from exc
    return resultado.stdout


def _descobrir_camada(mdb: Path) -> str:
    payload = json.loads(_executar_ogr(["ogrinfo", "-ro", "-json", str(mdb)]))
    camadas = payload.get("layers", [])
    if not camadas:
        raise RuntimeError("nenhuma camada encontrada no MDB")
    for camada in camadas:
        nome = str(camada.get("name", ""))
        if any(chave in nome.lower() for chave in ("localidade", "ponto", "feature")):
            return nome
    return str(camadas[0]["name"])


def _valor(propriedades: dict[str, Any], *nomes: str) -> Any:
    normalizadas = {str(chave).upper(): valor for chave, valor in propriedades.items()}
    for nome in nomes:
        valor = normalizadas.get(nome)
        if valor not in (None, ""):
            return valor
    return None


def _decimal(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    return float(str(valor).replace(",", "."))


def _ler_kml(kml: Path) -> list[dict[str, Any]]:
    root = ET.parse(kml).getroot()
    features: list[dict[str, Any]] = []
    for placemark in root.iter():
        if placemark.tag.rsplit("}", 1)[-1] != "Placemark":
            continue
        propriedades: dict[str, Any] = {}
        for elemento in placemark.iter():
            if elemento.tag.rsplit("}", 1)[-1] == "SimpleData" and elemento.get("name"):
                propriedades[elemento.get("name", "")] = (elemento.text or "").strip()
        nome = next(
            (
                elemento.text.strip()
                for elemento in placemark
                if elemento.tag.rsplit("}", 1)[-1] == "name" and elemento.text
            ),
            None,
        )
        if nome and "NM_LOCALIDADE" not in propriedades and "NM_LOCALID" not in propriedades:
            propriedades["NM_LOCALIDADE"] = nome
        coordenadas = next(
            (
                elemento.text.strip()
                for elemento in placemark.iter()
                if elemento.tag.rsplit("}", 1)[-1] == "coordinates" and elemento.text
            ),
            "",
        )
        features.append(
            {
                "properties": propriedades,
                "geometry": {"coordinates": coordenadas.split(",")[:3]},
            }
        )
    return features


def _importar_features(engine: object, features: list[dict[str, Any]]) -> int:
    inseridos = 0
    with engine.begin() as connection:
        municipios = {
            codigo: identificador
            for identificador, codigo in connection.execute(
                text("SELECT id, codigo_ibge FROM municipios")
            ).all()
        }
        if not municipios:
            raise RuntimeError("importe os municípios antes das localidades")
        for feature in features:
            propriedades = feature.get("properties") or {}
            codigo_municipio = str(
                _valor(propriedades, "CD_GEOCODMU", "CD_GEOCODM") or ""
            ).zfill(7)
            municipio_id = municipios.get(codigo_municipio)
            if municipio_id is None:
                continue
            coordenadas = (feature.get("geometry") or {}).get("coordinates") or []
            longitude = _decimal(_valor(propriedades, "LONG"))
            latitude = _decimal(_valor(propriedades, "LAT"))
            if len(coordenadas) >= 2:
                longitude = longitude if longitude is not None else _decimal(coordenadas[0])
                latitude = latitude if latitude is not None else _decimal(coordenadas[1])
            valores = {
                "id": _novo_id(),
                "codigo_setor": _valor(propriedades, "CD_GEOCODIGO", "CD_GEOCODI"),
                "municipio_id": municipio_id,
                "tipo": _valor(propriedades, "TIPO"),
                "bairro_codigo": _valor(propriedades, "CD_GEOCODBA", "CD_GEOCODB"),
                "bairro_nome": _valor(propriedades, "NM_BAIRRO"),
                "subdistrito_codigo": _valor(propriedades, "CD_GEOCODSD", "CD_GEOCODS"),
                "subdistrito_nome": _valor(propriedades, "NM_SUBDISTRITO", "NM_SUBDIST"),
                "distrito_codigo": _valor(propriedades, "CD_GEOCODDS", "CD_GEOCODD"),
                "distrito_nome": _valor(propriedades, "NM_DISTRITO", "NM_DISTRIT"),
                "microregiao_nome": _valor(propriedades, "NM_MICRO"),
                "mesoregiao_nome": _valor(propriedades, "NM_MESO"),
                "nivel_codigo": _valor(propriedades, "CD_NIVEL"),
                "categoria_codigo": _valor(propriedades, "CD_CATEGORIA", "CD_CATEGOR"),
                "categoria_nome": _valor(propriedades, "NM_CATEGORIA", "NM_CATEGOR"),
                "nome": _valor(propriedades, "NM_LOCALIDADE", "NM_LOCALID") or "Sem nome",
                "longitude": longitude,
                "latitude": latitude,
                "altitude_metros": _decimal(_valor(propriedades, "ALT")),
                "fonte": LOCALIDADES_FONTE,
                "ano_referencia": 2010,
            }
            connection.execute(
                text(
                    "INSERT INTO localidades (id, codigo_setor, municipio_id, tipo, "
                    "bairro_codigo, bairro_nome, subdistrito_codigo, subdistrito_nome, "
                    "distrito_codigo, distrito_nome, microregiao_nome, mesoregiao_nome, "
                    "nivel_codigo, categoria_codigo, categoria_nome, nome, longitude, latitude, "
                    "altitude_metros, fonte, ano_referencia) VALUES ("
                    ":id, :codigo_setor, :municipio_id, :tipo, :bairro_codigo, :bairro_nome, "
                    ":subdistrito_codigo, :subdistrito_nome, :distrito_codigo, :distrito_nome, "
                    ":microregiao_nome, :mesoregiao_nome, :nivel_codigo, :categoria_codigo, "
                    ":categoria_nome, :nome, :longitude, :latitude, :altitude_metros, :fonte, "
                    ":ano_referencia) ON CONFLICT (codigo_setor) DO NOTHING"
                ),
                valores,
            )
            inseridos += 1
    return inseridos


def importar_localidades(engine: object, mdb: Path) -> int:
    camada = _descobrir_camada(mdb)
    geojson = json.loads(
        _executar_ogr(["ogr2ogr", "-f", "GeoJSON", "/vsistdout/", str(mdb), camada])
    )
    return _importar_features(engine, geojson.get("features", []))


def importar_localidades_kml(engine: object, kml: Path) -> int:
    return _importar_features(engine, _ler_kml(kml))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--municipios", action="store_true")
    parser.add_argument("--localidades-mdb", type=Path)
    parser.add_argument("--localidades-kml", type=Path)
    args = parser.parse_args()
    if not args.municipios and args.localidades_mdb is None and args.localidades_kml is None:
        parser.error("informe --municipios, --localidades-mdb ou --localidades-kml")
    if args.localidades_mdb is not None and args.localidades_kml is not None:
        parser.error("escolha apenas uma fonte de localidades: MDB ou KML")
    if args.localidades_mdb is not None and not args.localidades_mdb.is_file():
        parser.error(f"MDB não encontrado: {args.localidades_mdb}")
    if args.localidades_kml is not None and not args.localidades_kml.is_file():
        parser.error(f"KML não encontrado: {args.localidades_kml}")
    engine = criar_engine(settings.database_url)
    if args.municipios:
        print(f"Municípios importados: {importar_municipios(engine)}")
    if args.localidades_mdb is not None:
        print(f"Localidades importadas: {importar_localidades(engine, args.localidades_mdb)}")
    if args.localidades_kml is not None:
        print(f"Localidades importadas: {importar_localidades_kml(engine, args.localidades_kml)}")


if __name__ == "__main__":
    main()
