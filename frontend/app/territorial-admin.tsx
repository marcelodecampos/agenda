"use client";

import { FormEvent, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";

type ApiFetch = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type Resource = "ufs" | "municipios";
type Item = { id: string; nome: string; [key: string]: unknown };
type Page = { items: Item[]; page: number; page_size: number; total: number; pages: number };
type Props = { apiFetch: ApiFetch; apiUrl: string };

const labels: Record<Resource, string> = { ufs: "Unidades de Federação", municipios: "Municípios" };
const endpoints: Record<Resource, string> = { ufs: "unidades-federacao", municipios: "municipios" };

function MunicipioLookup({ apiFetch, apiUrl, ufId, value, onChange, required = false, label }: Props & { ufId?: string; value: string; onChange: (id: string) => void; required?: boolean; label: string }) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Item[]>([]);
  const [selected, setSelected] = useState<Item | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!value) {
      setSelected(null);
      return;
    }
    const known = options.find((item) => item.id === value);
    if (known) {
      setSelected(known);
      return;
    }
    let active = true;
    void apiFetch(`${apiUrl}/admin/municipios/${value}`).then(async (response) => {
      if (active && response.ok) setSelected((await response.json()) as Item);
    });
    return () => { active = false; };
  }, [apiFetch, apiUrl, options, value]);

  useEffect(() => {
    const termo = query.trim();
    if (termo.length < 3) {
      setOptions([]);
      return;
    }
    const timer = window.setTimeout(() => {
      setLoading(true);
      const params = new URLSearchParams({ busca: termo, page: "1", page_size: "20" });
      if (ufId) params.set("unidade_federacao_id", ufId);
      void apiFetch(`${apiUrl}/admin/municipios?${params}`)
        .then(async (response) => {
          if (response.ok) setOptions(((await response.json()) as Page).items);
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [apiFetch, apiUrl, query, ufId]);

  function escolher(item: Item) {
    setSelected(item);
    setQuery("");
    setOptions([]);
    onChange(item.id);
  }

  return <div className="municipio-lookup">
    <span>{label}</span>
    {selected && <div className="municipio-selection"><strong>{selected.nome}</strong><small>{String(selected.codigo_ibge ?? "")}</small><button type="button" onClick={() => { setSelected(null); onChange(""); }} title="Limpar município" aria-label="Limpar município"><X size={13} /></button></div>}
    <input required={required && !value} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={selected ? "Trocar município" : "Digite ao menos 3 caracteres"} />
    {loading && <small className="lookup-status">Buscando...</small>}
    {!loading && query.trim().length > 0 && query.trim().length < 3 && <small className="lookup-status">Digite mais {3 - query.trim().length} caractere(s).</small>}
    {!!options.length && <div className="municipio-suggestions">{options.map((item) => <button type="button" key={item.id} onClick={() => escolher(item)}><strong>{item.nome}</strong><small>{String(item.codigo_ibge ?? "")}</small></button>)}</div>}
  </div>;
}

export default function TerritorialAdmin({ apiFetch, apiUrl }: Props) {
  const [resource, setResource] = useState<Resource>("ufs");
  const [page, setPage] = useState<Page>({ items: [], page: 1, page_size: 20, total: 0, pages: 1 });
  const [search, setSearch] = useState("");
  const [ufId, setUfId] = useState("");
  const [municipioId, setMunicipioId] = useState("");
  const [ufs, setUfs] = useState<Item[]>([]);
  const [editing, setEditing] = useState<Item | null>(null);
  const [form, setForm] = useState<Record<string, string>>({ nome: "", codigo_ibge: "", sigla: "", unidade_federacao_id: "", municipio_id: "", codigo_setor: "", latitude: "", longitude: "", categoria_nome: "" });
  const [editorOpen, setEditorOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadOptions() {
    const ufResponse = await apiFetch(`${apiUrl}/admin/unidades-federacao?page_size=100`);
    if (ufResponse.ok) setUfs(((await ufResponse.json()) as Page).items);
  }

  async function loadPage(nextPage = page.page) {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(nextPage), page_size: "20" });
    if (search.trim()) params.set("busca", search.trim());
    if (resource === "municipios" && ufId) params.set("unidade_federacao_id", ufId);
    try {
      const response = await apiFetch(`${apiUrl}/admin/${endpoints[resource]}?${params}`);
      if (!response.ok) throw new Error("Não foi possível carregar os dados territoriais.");
      setPage((await response.json()) as Page);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Não foi possível carregar os dados.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadOptions(); }, []);
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((position) => {
      const params = new URLSearchParams({ latitude: String(position.coords.latitude), longitude: String(position.coords.longitude) });
      void apiFetch(`${apiUrl}/admin/unidades-federacao-geolocalizacao?${params}`).then(async (response) => {
        if (response.ok) setUfId(((await response.json()) as Item).id);
      });
    }, () => undefined, { enableHighAccuracy: false, maximumAge: 300000, timeout: 5000 });
  }, [apiFetch, apiUrl]);
  useEffect(() => { void loadPage(1); }, [resource, search, ufId]);

  function selectResource(next: Resource) {
    setResource(next);
    setSearch("");
    setUfId("");
    setMunicipioId("");
    setEditorOpen(false);
  }

  function openEditor(item: Item | null) {
    setEditing(item);
    setForm({
      nome: String(item?.nome ?? ""),
      codigo_ibge: String(item?.codigo_ibge ?? ""),
      sigla: String(item?.sigla ?? ""),
      unidade_federacao_id: String(item?.unidade_federacao_id ?? ufId),
      municipio_id: String(item?.municipio_id ?? municipioId),
      codigo_setor: String(item?.codigo_setor ?? ""),
      latitude: String(item?.latitude ?? ""),
      longitude: String(item?.longitude ?? ""),
      categoria_nome: String(item?.categoria_nome ?? ""),
    });
    setEditorOpen(true);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const payload: Record<string, string | number | null> = { nome: form.nome };
    if (resource === "ufs") Object.assign(payload, { codigo_ibge: form.codigo_ibge, sigla: form.sigla });
    if (resource === "municipios") Object.assign(payload, { codigo_ibge: form.codigo_ibge, unidade_federacao_id: form.unidade_federacao_id });
    const response = await apiFetch(`${apiUrl}/admin/${endpoints[resource]}${editing ? `/${editing.id}` : ""}`, { method: editing ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) { setError("Não foi possível salvar o registro."); return; }
    setEditorOpen(false);
    setMessage(editing ? "Registro atualizado." : "Registro criado.");
    await loadOptions();
    await loadPage(editing ? page.page : 1);
  }

  async function remove(item: Item) {
    const response = await apiFetch(`${apiUrl}/admin/${endpoints[resource]}/${item.id}`, { method: "DELETE" });
    if (!response.ok) { setError("Não foi possível remover o registro. Verifique se existem dependências."); return; }
    setMessage("Registro removido.");
    await loadPage(page.page);
  }

  const fields = resource === "ufs"
    ? [["codigo_ibge", "Código IBGE"], ["sigla", "Sigla"], ["nome", "Nome"]]
    : resource === "municipios"
      ? [["codigo_ibge", "Código IBGE"], ["nome", "Nome"], ["unidade_federacao_id", "UF"]]
      : [["codigo_ibge", "Código IBGE"], ["nome", "Nome"], ["unidade_federacao_id", "UF"]];

  return <div className="territorial-admin">
    <div className="territorial-tabs">
      {(Object.keys(labels) as Resource[]).map((item) => <button key={item} type="button" className={resource === item ? "territorial-tab active" : "territorial-tab"} onClick={() => selectResource(item)}>{labels[item]}</button>)}
    </div>
    <div className="territorial-toolbar">
      <label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Buscar ${labels[resource].toLocaleLowerCase()}`} /></label>
      {resource === "municipios" && <select value={ufId} onChange={(event) => { setUfId(event.target.value); setMunicipioId(""); }}><option value="">Todas as UFs</option>{ufs.map((item) => <option key={item.id} value={item.id}>{String(item.sigla)} · {item.nome}</option>)}</select>}
      <button className="icon-action add-icon" type="button" onClick={() => openEditor(null)} title="Adicionar" aria-label="Adicionar"><Plus size={18} /></button>
    </div>
    {editorOpen && <form className="territorial-editor" onSubmit={(event) => void save(event)}>{fields.map(([key, label]) => <label key={key}><span>{label}</span>{key === "unidade_federacao_id" ? <select required value={form[key]} onChange={(event) => setForm({ ...form, unidade_federacao_id: event.target.value, municipio_id: "" })}><option value="">Selecione</option>{ufs.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select> : key === "municipio_id" ? <MunicipioLookup apiFetch={apiFetch} apiUrl={apiUrl} ufId={form.unidade_federacao_id} value={form[key]} onChange={(id) => setForm({ ...form, municipio_id: id })} required label={label} /> : <input required={key === "nome" || key === "codigo_ibge" || key === "sigla"} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />}</label>)}<div className="editor-actions"><button className="icon-action save-action" type="submit" title="Salvar" aria-label="Salvar"><Save size={17} /></button><button className="icon-action cancel-action" type="button" onClick={() => setEditorOpen(false)} title="Cancelar" aria-label="Cancelar"><X size={17} /></button></div></form>}
    {error && <p className="admin-error" role="alert">{error}</p>}{message && <p className="admin-success" role="status">{message}</p>}
    <div className="territorial-table">{loading ? <p>Carregando...</p> : page.items.map((item) => <div className="territorial-row" key={item.id}><div><strong>{item.nome}</strong><small>{resource === "ufs" ? `${String(item.sigla)} · ${String(item.codigo_ibge)}` : String(item.codigo_ibge)}</small></div><div className="row-actions"><button className="icon-action subtle" type="button" onClick={() => openEditor(item)} title="Editar" aria-label="Editar"><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" onClick={() => void remove(item)} title="Remover" aria-label="Remover"><Trash2 size={15} /></button></div></div>)}</div>
    {page.total > 0 && <div className="catalog-pagination"><span className="catalog-range">Página {page.page} de {page.pages} · {page.total} registros</span><div className="page-buttons"><button type="button" disabled={page.page <= 1} onClick={() => void loadPage(page.page - 1)} title="Anterior" aria-label="Anterior"><ChevronLeft size={15} /></button><button type="button" disabled={page.page >= page.pages} onClick={() => void loadPage(page.page + 1)} title="Próxima" aria-label="Próxima"><ChevronRight size={15} /></button></div></div>}
  </div>;
}
