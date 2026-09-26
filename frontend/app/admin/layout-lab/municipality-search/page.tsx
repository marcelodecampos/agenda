"use client";

import { App, Button, Card, Empty, Input, Result, Select, Space, Spin, Table, Tag, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useEffect, useRef, useState } from "react";

import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { useAuth } from "../../../auth-provider";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";
const MIN_SEARCH_LENGTH = 3;
const DEBOUNCE_MS = 300;

type FederativeUnit = { id: string; name: string; abbreviation: string };
type Municipality = {
  id: string;
  ibge_code: string;
  name: string;
  federative_unit_id: string;
  federative_unit_abbreviation: string;
  federative_unit_name: string;
};
type SearchResponse = { source: "opensearch" | "postgresql"; items: Municipality[] };

const groups = [
  {
    id: "municipality-search-group-tables",
    label: "Tabelas",
    items: [
      { id: "municipality-search-nav-gender", label: "Gênero", href: "/admin/genders" },
      { id: "municipality-search-nav-locality", label: "Localidade", href: "/admin/localities" },
    ],
  },
  {
    id: "municipality-search-group-people",
    label: "Pessoa",
    items: [
      { id: "municipality-search-nav-person", label: "Pessoa física", href: "/admin/people" },
      { id: "municipality-search-nav-company", label: "Pessoa jurídica", href: "/admin/people" },
    ],
  },
  {
    id: "municipality-search-group-layout",
    label: "Elementos de layout",
    items: [
      { id: "municipality-search-nav-buttons", label: "Botões", href: "/admin/button-lab" },
      { id: "municipality-search-nav-layout-lab", label: "Laboratório de layout", href: "/admin/layout-lab" },
      { id: "municipality-search-nav-address", label: "Diálogo de endereço", href: "/admin/layout-lab/address-dialog" },
      { id: "municipality-search-nav-current", label: "Consulta de município", href: "/admin/layout-lab/municipality-search", active: true },
    ],
  },
];

const columns: TableColumnsType<Municipality> = [
  { title: "Município", dataIndex: "name", key: "name" },
  {
    title: "UF",
    key: "federative_unit",
    render: (_, item) => `${item.federative_unit_abbreviation} - ${item.federative_unit_name}`,
  },
  { title: "Código IBGE", dataIndex: "ibge_code", key: "ibge_code", width: 140 },
];

export default function MunicipalitySearchPage() {
  const { authenticated, loading, login, apiFetch } = useAuth();
  const [federativeUnits, setFederativeUnits] = useState<FederativeUnit[]>([]);
  const [federativeUnitId, setFederativeUnitId] = useState<string | undefined>();
  const [text, setText] = useState("");
  const [limit, setLimit] = useState(10);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);

  useEffect(() => {
    if (!authenticated) return;
    void (async () => {
      const response = await apiFetch(`${API_URL}/search/federative-units`);
      if (response.ok) setFederativeUnits((await response.json()) as FederativeUnit[]);
    })();
  }, [authenticated, apiFetch]);

  useEffect(() => {
    const term = text.trim();
    const sequence = ++requestSequence.current;
    if (!authenticated || term.length < MIN_SEARCH_LENGTH) return;
    const timer = setTimeout(async () => {
      setSearching(true);
      setError(null);
      const params = new URLSearchParams({ q: term, limit: String(limit) });
      if (federativeUnitId) params.set("federative_unit_id", federativeUnitId);
      try {
        const response = await apiFetch(`${API_URL}/search/municipalities?${params}`);
        if (sequence !== requestSequence.current) return;
        if (!response.ok) {
          setError("Não foi possível consultar os municípios.");
          setResult(null);
          return;
        }
        setResult((await response.json()) as SearchResponse);
      } catch {
        if (sequence === requestSequence.current) setError("Não foi possível consultar os municípios.");
      } finally {
        if (sequence === requestSequence.current) setSearching(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, federativeUnitId, limit, authenticated, apiFetch]);

  const searchActive = authenticated && text.trim().length >= MIN_SEARCH_LENGTH;
  const visibleResult = searchActive ? result : null;
  const visibleSearching = searchActive && searching;
  const visibleError = searchActive ? error : null;

  function renderContent() {
    if (loading) return <div id="municipality-search-loading"><Spin /></div>;
    if (!authenticated) {
      return (
        <div id="municipality-search-login-required">
          <Result
            status="403"
            title="Login necessário"
            subTitle="A consulta de municípios está disponível apenas para usuários autenticados."
            extra={<Button id="municipality-search-login" type="primary" onClick={() => void login()}>Entrar</Button>}
          />
        </div>
      );
    }
    return (
      <Card id="municipality-search-card">
        <Space id="municipality-search-filters" wrap size="middle" style={{ marginBottom: 16 }}>
          <Select
            id="municipality-search-state"
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Todas as UFs"
            style={{ width: 240 }}
            value={federativeUnitId}
            onChange={setFederativeUnitId}
            options={federativeUnits.map((unit) => ({ value: unit.id, label: `${unit.abbreviation} - ${unit.name}` }))}
          />
          <Input.Search
            id="municipality-search-text"
            allowClear
            autoComplete="off"
            placeholder="Digite pelo menos 3 letras"
            style={{ width: 320 }}
            value={text}
            loading={visibleSearching}
            onChange={(event) => setText(event.target.value)}
          />
          <Select
            id="municipality-search-limit"
            style={{ width: 140 }}
            value={limit}
            onChange={setLimit}
            options={[5, 10, 20, 50].map((value) => ({ value, label: `${value} resultados` }))}
          />
          {visibleResult && (
            <Tag id="municipality-search-source" color={visibleResult.source === "opensearch" ? "green" : "orange"}>
              {visibleResult.source === "opensearch" ? "OpenSearch" : "PostgreSQL (alternativa)"}
            </Tag>
          )}
        </Space>
        {visibleError && <Typography.Paragraph id="municipality-search-error" type="danger">{visibleError}</Typography.Paragraph>}
        <Table
          id="municipality-search-results"
          rowKey="id"
          size="small"
          columns={columns}
          dataSource={visibleResult?.items ?? []}
          loading={visibleSearching}
          pagination={false}
          locale={{
            emptyText: (
              <Empty
                description={text.trim().length < MIN_SEARCH_LENGTH ? "Digite pelo menos 3 letras para consultar." : "Nenhum município encontrado."}
              />
            ),
          }}
        />
      </Card>
    );
  }

  return (
    <App>
      <main id="municipality-search-page" className="admin-area">
        <AdminSidebar id="municipality-search-sidebar" groups={groups} />
        <section id="municipality-search-content" className="admin-content">
          <Typography.Title id="municipality-search-title" level={2}>Consulta de município</Typography.Title>
          <Typography.Paragraph id="municipality-search-description" type="secondary">
            Busca pelo nome com tolerância a acentos e erros de digitação. Usa o OpenSearch e, se ele estiver indisponível, o PostgreSQL.
          </Typography.Paragraph>
          {renderContent()}
        </section>
      </main>
    </App>
  );
}
