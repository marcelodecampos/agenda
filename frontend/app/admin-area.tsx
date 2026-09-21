"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";
import { useAuth } from "./auth-provider";
import TerritorialAdmin from "./territorial-admin";

type CategoriaServico = { id: string; nome: string };
type NomeServico = { id: string; nome: string; categorias?: CategoriaServico[] };
type CatalogoItem = { id: string; nome: string };
type UnidadeFederacaoItem = CatalogoItem & { sigla: string };
type UsuarioAdmin = { id: string; nome: string; email?: string | null; cpf?: string | null; telefone?: string | null; provider: string; subject: string };
type OrganizacaoAdmin = { id: string; nome: string; nome_fantasia?: string | null; cnpj?: string | null; unipessoal: boolean; endereco?: { logradouro: string; numero: string; cidade: string; estado: string; cep: string; bairro?: string | null; descricao?: string; municipio_id?: string | null } | null; especialidades?: CatalogoItem[] };
type EnderecoAdmin = { logradouro: string; numero: string; cidade: string; estado: string; cep: string; bairro?: string | null; tipo?: string; descricao?: string; principal?: boolean };
type AdminAreaProps = { userName: string | null; logout: () => Promise<void> };
type EnderecoForm = { logradouro: string; numero: string; cidade: string; estado: string; cep: string; bairro: string; descricao: string; uf_id: string; municipio_id: string };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

function formatarCnpj(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 14);
  return digits
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3/$4")
    .replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, "$1.$2.$3/$4-$5");
}

function ConsultaCep({ apiFetch, cep, onChange }: { apiFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>; cep: string; onChange: (endereco: Partial<EnderecoForm>) => void }) {
  const [consultando, setConsultando] = useState(false);
  const [erroCep, setErroCep] = useState("");

  async function consultar() {
    const digits = cep.replace(/\D/g, "");
    if (digits.length !== 8) {
      setErroCep("Informe um CEP com 8 dígitos.");
      return;
    }
    setConsultando(true);
    setErroCep("");
    try {
      const resposta = await apiFetch(`${apiUrl}/admin/enderecos/cep/${digits}`);
      if (!resposta.ok) throw new Error("CEP não encontrado.");
      const dados = await resposta.json() as { logradouro?: string; bairro?: string; municipio?: string; uf?: string };
      onChange({ logradouro: dados.logradouro ?? "", bairro: dados.bairro ?? "", cidade: dados.municipio ?? "", estado: dados.uf ?? "" });
    } catch (error) {
      setErroCep(error instanceof Error ? error.message : "Não foi possível consultar o CEP.");
    } finally {
      setConsultando(false);
    }
  }

  return <div className="cep-lookup"><label><span>CEP</span><span className="cep-input-shell"><input value={cep} onChange={(event) => onChange({ cep: event.target.value })} placeholder="00000-000" inputMode="numeric" /><button className="cep-search-button" type="button" onClick={() => void consultar()} disabled={consultando} title="Consultar CEP" aria-label="Consultar CEP"><Search size={16} /></button></span></label>{erroCep && <small role="alert">{erroCep}</small>}</div>;
}

function EnderecoFields({ apiFetch, endereco, onChange }: { apiFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>; endereco: EnderecoForm; onChange: (patch: Partial<EnderecoForm>) => void }) {
  const [ufs, setUfs] = useState<UnidadeFederacaoItem[]>([]);
  const [municipios, setMunicipios] = useState<CatalogoItem[]>([]);
  const [municipioBusca, setMunicipioBusca] = useState("");

  useEffect(() => { void apiFetch(`${apiUrl}/admin/unidades-federacao?page_size=100`).then(async (response) => { if (response.ok) setUfs(((await response.json()).items ?? []) as UnidadeFederacaoItem[]); }); }, [apiFetch]);
  useEffect(() => {
    if (!endereco.uf_id || municipioBusca.trim().length < 3) { setMunicipios([]); return; }
    const timer = window.setTimeout(() => void apiFetch(`${apiUrl}/admin/municipios?busca=${encodeURIComponent(municipioBusca.trim())}&unidade_federacao_id=${endereco.uf_id}&page_size=20`).then(async (response) => { if (response.ok) setMunicipios(((await response.json()).items ?? []) as CatalogoItem[]); }), 250);
    return () => window.clearTimeout(timer);
  }, [apiFetch, endereco.uf_id, municipioBusca]);
  useEffect(() => {
    if (endereco.uf_id || !endereco.estado || !ufs.length) return;
    const estado = ufs.find((item) => item.nome.toLocaleLowerCase() === endereco.estado.toLocaleLowerCase() || item.sigla.toLocaleLowerCase() === endereco.estado.toLocaleLowerCase());
    if (estado) onChange({ uf_id: estado.id, estado: estado.sigla });
  }, [endereco.estado, endereco.uf_id, onChange, ufs]);

  return <div className="address-fields">
    <div className="address-row"><label><span>Descrição do endereço <small>(opcional)</small></span><input value={endereco.descricao} onChange={(event) => onChange({ descricao: event.target.value })} placeholder="Ex.: Matriz, Casa, Trabalho" maxLength={40} /></label></div>
    <div className="address-row address-row-cep"><ConsultaCep apiFetch={apiFetch} cep={endereco.cep} onChange={onChange} /><label><span>Estado</span><select value={endereco.uf_id} onChange={(event) => { const estado = ufs.find((item) => item.id === event.target.value); onChange({ uf_id: event.target.value, municipio_id: "", estado: estado?.sigla ?? "" }); }}><option value="">Selecione o estado</option>{ufs.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label></div>
    <div className="address-row"><label><span>Cidade</span><input value={municipioBusca || endereco.cidade} onChange={(event) => { setMunicipioBusca(event.target.value); onChange({ cidade: event.target.value, municipio_id: "" }); }} placeholder="Digite ao menos 3 caracteres" disabled={!endereco.uf_id} /></label><div className="address-suggestions">{municipios.map((item) => <button type="button" key={item.id} onClick={() => { onChange({ municipio_id: item.id, cidade: item.nome }); setMunicipioBusca(item.nome); setMunicipios([]); }}>{item.nome}</button>)}</div></div>
    <div className="address-row address-row-main"><label><span>Logradouro</span><input value={endereco.logradouro} onChange={(event) => onChange({ logradouro: event.target.value })} placeholder="Rua, avenida, praça..." /></label><label><span>Número</span><input value={endereco.numero} onChange={(event) => onChange({ numero: event.target.value })} /></label></div>
    <div className="address-row"><label><span>Bairro <small>(opcional)</small></span><input value={endereco.bairro} onChange={(event) => onChange({ bairro: event.target.value })} /></label></div>
  </div>;
}

export default function AdminArea({ userName, logout }: AdminAreaProps) {
  const { apiFetch } = useAuth();
  const [section, setSection] = useState<"overview" | "catalog" | "users" | "organizations" | "professionals" | "territorial">("overview");
  const [catalogKind, setCatalogKind] = useState<"names" | "categories" | "specialties">("names");
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [buscaOpen, setBuscaOpen] = useState(false);
  const [exclusaoPendente, setExclusaoPendente] = useState<CatalogoItem[] | null>(null);
  const [termoBusca, setTermoBusca] = useState("");
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [nomes, setNomes] = useState<NomeServico[]>([]);
  const [categorias, setCategorias] = useState<CategoriaServico[]>([]);
  const [especialidades, setEspecialidades] = useState<CatalogoItem[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [organizacoes, setOrganizacoes] = useState<OrganizacaoAdmin[]>([]);
  const [especialidadesCatalogo, setEspecialidadesCatalogo] = useState<CatalogoItem[]>([]);
  const [formUsuarioAberto, setFormUsuarioAberto] = useState(false);
  const [usuarioEmEdicao, setUsuarioEmEdicao] = useState<UsuarioAdmin | null>(null);
  const [usuarioForm, setUsuarioForm] = useState({ provider: "keycloak", subject: "", nome: "", cpf: "", email: "", telefone: "" });
  const [formOrganizacaoAberto, setFormOrganizacaoAberto] = useState(false);
  const [organizacaoEmEdicao, setOrganizacaoEmEdicao] = useState<OrganizacaoAdmin | null>(null);
  const [organizacaoTab, setOrganizacaoTab] = useState<"dados" | "enderecos">("dados");
  const [enderecosOrganizacao, setEnderecosOrganizacao] = useState<EnderecoAdmin[]>([]);
  const [adicionandoEndereco, setAdicionandoEndereco] = useState(false);
  const [novoEnderecoPrincipal, setNovoEnderecoPrincipal] = useState(false);
  const [organizacaoForm, setOrganizacaoForm] = useState({ nome: "", nome_fantasia: "", cnpj: "", unipessoal: false, logradouro: "", numero: "", cidade: "", estado: "", cep: "", bairro: "", descricao: "Matriz", uf_id: "", municipio_id: "", especialidade_ids: [] as string[] });
  const [formProfissionalAberto, setFormProfissionalAberto] = useState(false);
  const [profissionalForm, setProfissionalForm] = useState({ nome: "", logradouro: "", numero: "", cidade: "", estado: "", cep: "", bairro: "", descricao: "Casa", uf_id: "", municipio_id: "", especialidade_ids: [] as string[] });
  const [nomesSelecionados, setNomesSelecionados] = useState<Set<string>>(new Set());
  const [novoNome, setNovoNome] = useState("");
  const [nomeEmEdicao, setNomeEmEdicao] = useState<NomeServico | null>(null);
  const [categoriaIdsEmEdicao, setCategoriaIdsEmEdicao] = useState<string[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const nomesSelecionadosLista = nomes.filter((nome) => nomesSelecionados.has(nome.id));
  const registrosPorPagina = 20;
  const catalogLabel = catalogKind === "names" ? "nomes de serviço" : catalogKind === "categories" ? "categorias" : "especialidades";
  const catalogTitle = catalogKind === "names" ? "Nomes de Serviço" : catalogKind === "categories" ? "Categorias" : "Especialidades";
  const catalogEndpoint = catalogKind === "names" ? "nomes-servico" : catalogKind === "categories" ? "categorias-servico" : "especialidades";
  const nomesFiltrados = nomes
    .filter((nome) => nome.nome.toLocaleLowerCase().includes(termoBusca.trim().toLocaleLowerCase()))
    .sort((primeiro, segundo) => primeiro.nome.localeCompare(segundo.nome, "pt-BR", { sensitivity: "base" }));
  const totalPaginas = Math.max(1, Math.ceil(nomesFiltrados.length / registrosPorPagina));
  const paginaSegura = Math.min(paginaAtual, totalPaginas);
  const primeiroRegistro = nomesFiltrados.length ? (paginaSegura - 1) * registrosPorPagina : 0;
  const nomesDaPagina = nomesFiltrados.slice(primeiroRegistro, primeiroRegistro + registrosPorPagina);
  const ultimoRegistro = Math.min(primeiroRegistro + nomesDaPagina.length, nomesFiltrados.length);

  const carregarNomes = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const resposta = await apiFetch(`${apiUrl}/catalogo/${catalogEndpoint}`);
      if (!resposta.ok) throw new Error("Não foi possível carregar o catálogo.");
      const itens = (await resposta.json()) as NomeServico[];
      setNomes(itens);
      if (catalogKind === "specialties") {
        setEspecialidades(itens as CatalogoItem[]);
      }
    } catch {
      setErro(`Não foi possível carregar ${catalogLabel}.`);
    } finally {
      setCarregando(false);
    }
  }, [apiFetch, catalogEndpoint, catalogKind, catalogLabel]);

  const carregarCategorias = useCallback(async () => {
    try {
      const resposta = await apiFetch(`${apiUrl}/catalogo/categorias-servico`);
      if (resposta.ok) setCategorias((await resposta.json()) as CategoriaServico[]);
    } catch {
      setCategorias([]);
    }
  }, [apiFetch]);

  useEffect(() => {
    const tarefa = window.setTimeout(() => void carregarNomes(), 0);
    return () => window.clearTimeout(tarefa);
  }, [carregarNomes]);

  useEffect(() => {
    const tarefa = window.setTimeout(() => void carregarCategorias(), 0);
    return () => window.clearTimeout(tarefa);
  }, [carregarCategorias]);

  useEffect(() => {
    if (catalogKind !== "specialties") return;
    const tarefa = window.setTimeout(() => void carregarNomes(), 0);
    return () => window.clearTimeout(tarefa);
  }, [carregarNomes, catalogKind]);

  useEffect(() => {
    if (section !== "users") return;
    void (async () => {
      try {
        const resposta = await apiFetch(`${apiUrl}/usuarios`);
        if (!resposta.ok) throw new Error("Não foi possível carregar usuários.");
        setUsuarios((await resposta.json()) as UsuarioAdmin[]);
      } catch {
        setUsuarios([]);
      }
    })();
  }, [apiFetch, section]);

  useEffect(() => {
    void (async () => {
      try {
        const resposta = await apiFetch(`${apiUrl}/catalogo/especialidades`);
        if (resposta.ok) setEspecialidadesCatalogo((await resposta.json()) as CatalogoItem[]);
      } catch {
        setEspecialidadesCatalogo([]);
      }
    })();
  }, [apiFetch]);

  useEffect(() => {
    if (section !== "organizations" && section !== "professionals") return;
    void (async () => {
      try {
        const resposta = await apiFetch(`${apiUrl}/organizacoes`);
        if (!resposta.ok) throw new Error("Não foi possível carregar organizações.");
        const itens = (await resposta.json()) as OrganizacaoAdmin[];
        setOrganizacoes(itens);
      } catch {
        setOrganizacoes([]);
      }
    })();
  }, [apiFetch, section]);

  useEffect(() => {
    if (!mensagem) return;
    const temporizador = window.setTimeout(() => setMensagem(""), 3000);
    return () => window.clearTimeout(temporizador);
  }, [mensagem]);

  useEffect(() => {
    if (!erro) return;
    const temporizador = window.setTimeout(() => setErro(""), 5000);
    return () => window.clearTimeout(temporizador);
  }, [erro]);

  async function salvarNome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nome = nomeEmEdicao?.nome ?? novoNome;
    if (!nome.trim()) return;
    setSalvando(true);
    setErro("");
    setMensagem("");
    const editando = nomeEmEdicao !== null;
    try {
      const resposta = await apiFetch(
        editando ? `${apiUrl}/catalogo/${catalogEndpoint}/${nomeEmEdicao.id}` : `${apiUrl}/catalogo/${catalogEndpoint}`,
        { method: editando ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome: nome.trim(), ...(catalogKind === "names" ? { categoria_ids: categoriaIdsEmEdicao } : {}) }) },
      );
      if (!resposta.ok) {
        if (resposta.status === 409) throw new Error(`Essa ${catalogKind === "names" ? "nome" : "categoria"} já está cadastrada.`);
        throw new Error(`Não foi possível salvar ${catalogKind === "names" ? "o nome" : "a categoria"}.`);
      }
      fecharEditor();
      setMensagem(editando ? `${catalogTitle.slice(0, -1)} atualizado.` : `${catalogTitle.slice(0, -1)} criado.`);
      await carregarNomes();
    } catch (error) {
      setErro(error instanceof TypeError ? "Não foi possível conectar à API. Verifique se o backend está em execução." : error instanceof Error ? error.message : "Não foi possível salvar o nome.");
    } finally {
      setSalvando(false);
    }
  }

  function fecharEditor() {
    setEditorOpen(false);
    setNomeEmEdicao(null);
    setNovoNome("");
    setCategoriaIdsEmEdicao([]);
  }

  function abrirNovoNome() {
    setNomeEmEdicao(null);
    setNovoNome("");
    setCategoriaIdsEmEdicao([]);
    setEditorOpen(true);
  }

  function abrirEdicao(nome: NomeServico) {
    setNomesSelecionados(new Set([nome.id]));
    setNomeEmEdicao(nome);
    setCategoriaIdsEmEdicao(nome.categorias?.map((categoria) => categoria.id) ?? []);
    setEditorOpen(true);
  }

  function alternarCategoria(categoriaId: string) {
    setCategoriaIdsEmEdicao((selecionadas) => selecionadas.includes(categoriaId)
      ? selecionadas.filter((id) => id !== categoriaId)
      : [...selecionadas, categoriaId]);
  }

  async function removerNome(nomeServico: CatalogoItem) {
    setExclusaoPendente([nomeServico]);
  }

  async function confirmarExclusao() {
    if (!exclusaoPendente?.length) return;
    setErro("");
    setMensagem("");
    const respostas = await Promise.all(
      exclusaoPendente.map((nome) => apiFetch(`${apiUrl}/catalogo/${catalogEndpoint}/${nome.id}`, { method: "DELETE" })),
    );
    const falhou = respostas.find((resposta) => !resposta.ok);
    if (falhou) {
      setErro(falhou.status === 409 ? `Este item está sendo usado por um serviço e não pode ser removido.` : `Não foi possível remover ${catalogLabel}.`);
      setExclusaoPendente(null);
      return;
    }
    setNomesSelecionados(new Set());
    setExclusaoPendente(null);
    setMensagem(exclusaoPendente.length === 1 ? `${catalogTitle.slice(0, -1)} removido.` : `${exclusaoPendente.length} itens removidos.`);
    await carregarNomes();
  }

  function alternarSelecao(nome: CatalogoItem) {
    setNomesSelecionados((selecionados) => {
      const proximaSelecao = new Set(selecionados);
      if (proximaSelecao.has(nome.id)) {
        proximaSelecao.delete(nome.id);
      } else {
        proximaSelecao.add(nome.id);
      }
      return proximaSelecao;
    });
  }

  function aplicarSelecao(ids: Set<string>) {
    setNomesSelecionados(ids);
    if (ids.size !== 1) {
      fecharEditor();
    }
  }

  function selecionarTodos() {
    aplicarSelecao(new Set(nomes.map((nome) => nome.id)));
  }

  function selecionarNenhum() {
    aplicarSelecao(new Set());
  }

  function inverterSelecao() {
    const invertidos = new Set(
      nomes.filter((nome) => !nomesSelecionados.has(nome.id)).map((nome) => nome.id),
    );
    aplicarSelecao(invertidos);
  }

  async function removerSelecionados() {
    const quantidade = nomesSelecionadosLista.length;
    if (quantidade) setExclusaoPendente(nomesSelecionadosLista);
  }

  async function removerUsuario(usuarioId: string) {
    try {
      const resposta = await apiFetch(`${apiUrl}/usuarios/${usuarioId}`, { method: "DELETE" });
      if (!resposta.ok) throw new Error("Não foi possível remover o usuário.");
      setUsuarios((atual) => atual.filter((usuario) => usuario.id !== usuarioId));
      setMensagem("Usuário removido.");
    } catch {
      setErro("Não foi possível remover o usuário.");
    }
  }

  function abrirNovoUsuario() {
    setUsuarioEmEdicao(null);
    setUsuarioForm({ provider: "keycloak", subject: "", nome: "", cpf: "", email: "", telefone: "" });
    setFormUsuarioAberto(true);
  }

  function abrirEdicaoUsuario(usuario: UsuarioAdmin) {
    setUsuarioEmEdicao(usuario);
    setUsuarioForm({
      provider: usuario.provider,
      subject: usuario.subject,
      nome: usuario.nome,
      cpf: usuario.cpf ?? "",
      email: usuario.email ?? "",
      telefone: usuario.telefone ?? "",
    });
    setFormUsuarioAberto(true);
  }

  async function salvarUsuario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = {
        provider: usuarioForm.provider,
        subject: usuarioForm.subject,
        nome: usuarioForm.nome,
        cpf: usuarioForm.cpf || null,
        email: usuarioForm.email || null,
        telefone: usuarioForm.telefone || null,
      };
      const url = usuarioEmEdicao ? `${apiUrl}/usuarios/${usuarioEmEdicao.id}` : `${apiUrl}/usuarios`;
      const resposta = await apiFetch(url, {
        method: usuarioEmEdicao ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resposta.ok) throw new Error("Não foi possível salvar o usuário.");
      const salvo = (await resposta.json()) as UsuarioAdmin;
      setUsuarios((atual) => usuarioEmEdicao ? atual.map((item) => item.id === salvo.id ? salvo : item) : [salvo, ...atual]);
      setFormUsuarioAberto(false);
      setMensagem(usuarioEmEdicao ? "Usuário atualizado." : "Usuário criado.");
    } catch {
      setErro("Não foi possível salvar o usuário.");
    }
  }

  async function removerOrganizacao(organizacaoId: string) {
    try {
      const resposta = await apiFetch(`${apiUrl}/organizacoes/${organizacaoId}`, { method: "DELETE" });
      if (!resposta.ok) throw new Error("Não foi possível remover a organização.");
      setOrganizacoes((atual) => atual.filter((organizacao) => organizacao.id !== organizacaoId));
      setMensagem("Organização removida.");
    } catch {
      setErro("Não foi possível remover a organização.");
    }
  }

  function abrirNovaOrganizacao() {
    setOrganizacaoEmEdicao(null);
    setOrganizacaoForm({ nome: "", nome_fantasia: "", cnpj: "", unipessoal: false, logradouro: "", numero: "", cidade: "", estado: "", cep: "", bairro: "", descricao: "Matriz", uf_id: "", municipio_id: "", especialidade_ids: [] });
    setFormOrganizacaoAberto(true);
    setOrganizacaoTab("dados");
    setEnderecosOrganizacao([]);
    setAdicionandoEndereco(false);
    setNovoEnderecoPrincipal(false);
  }

  function abrirEdicaoOrganizacao(organizacao: OrganizacaoAdmin) {
    setOrganizacaoEmEdicao(organizacao);
    setOrganizacaoForm({
      nome: organizacao.nome,
      nome_fantasia: organizacao.nome_fantasia ?? "",
      cnpj: organizacao.cnpj ?? "",
      unipessoal: organizacao.unipessoal,
      logradouro: organizacao.endereco?.logradouro ?? "",
      bairro: organizacao.endereco?.bairro ?? "",
      numero: organizacao.endereco?.numero ?? "",
      cidade: organizacao.endereco?.cidade ?? "",
      estado: organizacao.endereco?.estado ?? "",
      cep: organizacao.endereco?.cep ?? "",
      descricao: organizacao.endereco?.descricao ?? "Matriz", uf_id: "", municipio_id: organizacao.endereco?.municipio_id ?? "", especialidade_ids: organizacao.especialidades?.map((item) => item.id) ?? [],
    });
    setFormOrganizacaoAberto(true);
    setOrganizacaoTab("dados");
    setAdicionandoEndereco(false);
    setNovoEnderecoPrincipal(false);
    void apiFetch(`${apiUrl}/admin/cadastros/${organizacao.id}/enderecos`).then(async (response) => {
      if (response.ok) setEnderecosOrganizacao((await response.json()) as EnderecoAdmin[]);
    });
  }

  async function salvarOrganizacao(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = {
        nome: organizacaoForm.nome,
        nome_fantasia: organizacaoForm.nome_fantasia || null,
        cnpj: organizacaoForm.cnpj || null,
        unipessoal: organizacaoForm.unipessoal,
        endereco: null,
        especialidade_ids: organizacaoForm.especialidade_ids,
      };
      const url = organizacaoEmEdicao ? `${apiUrl}/organizacoes/${organizacaoEmEdicao.id}` : `${apiUrl}/organizacoes`;
      const resposta = await apiFetch(url, {
        method: organizacaoEmEdicao ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resposta.ok) throw new Error("Não foi possível salvar a organização.");
      const salvo = (await resposta.json()) as OrganizacaoAdmin;
      setOrganizacoes((atual) => organizacaoEmEdicao ? atual.map((item) => item.id === salvo.id ? salvo : item) : [salvo, ...atual]);
      setFormOrganizacaoAberto(false);
      setMensagem(organizacaoEmEdicao ? "Organização atualizada." : "Organização criada.");
    } catch {
      setErro("Não foi possível salvar a organização.");
    }
  }

  async function adicionarEnderecoOrganizacao() {
    if (!organizacaoEmEdicao) return;
    const resposta = await apiFetch(`${apiUrl}/admin/cadastros/${organizacaoEmEdicao.id}/endereco`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ logradouro: organizacaoForm.logradouro, numero: organizacaoForm.numero, cidade: organizacaoForm.cidade, estado: organizacaoForm.estado, cep: organizacaoForm.cep, bairro: organizacaoForm.bairro || null, municipio_id: organizacaoForm.municipio_id || null, tipo: "unidade", descricao: organizacaoForm.descricao, principal: novoEnderecoPrincipal }),
    });
    if (!resposta.ok) { setErro("Não foi possível adicionar o endereço."); return; }
    const lista = await apiFetch(`${apiUrl}/admin/cadastros/${organizacaoEmEdicao.id}/enderecos`);
    if (lista.ok) setEnderecosOrganizacao((await lista.json()) as EnderecoAdmin[]);
    setAdicionandoEndereco(false);
    setNovoEnderecoPrincipal(false);
    setMensagem("Endereço adicionado.");
  }

  function abrirNovoProfissional() {
    setProfissionalForm({ nome: "", logradouro: "", numero: "", cidade: "", estado: "", cep: "", bairro: "", descricao: "Casa", uf_id: "", municipio_id: "", especialidade_ids: [] });
    setFormProfissionalAberto(true);
  }

  async function salvarProfissional(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = {
        nome: profissionalForm.nome,
        endereco: profissionalForm.logradouro || profissionalForm.cidade ? {
          logradouro: profissionalForm.logradouro,
          numero: profissionalForm.numero,
          cidade: profissionalForm.cidade,
          estado: profissionalForm.estado,
          cep: profissionalForm.cep,
          bairro: profissionalForm.bairro || null,
          unidade_federacao_id: profissionalForm.uf_id || null,
          municipio_id: profissionalForm.municipio_id || null,
        } : null,
        especialidade_ids: profissionalForm.especialidade_ids,
      };
      const resposta = await apiFetch(`${apiUrl}/profissionais/independente`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resposta.ok) throw new Error("Não foi possível salvar o profissional.");
      const salvo = (await resposta.json()) as { organizacao: OrganizacaoAdmin };
      setOrganizacoes((atual) => [salvo.organizacao, ...atual]);
      setFormProfissionalAberto(false);
      setMensagem("Profissional criado.");
    } catch {
      setErro("Não foi possível salvar o profissional.");
    }
  }

  function renderEditor() {
    return (
      <form className="catalog-editor catalog-editor-full" onSubmit={salvarNome}>
        <div className="editor-heading">
          <div>
            <p className="eyebrow">{nomeEmEdicao ? "Edição" : "Novo registro"}</p>
            <h4>{nomeEmEdicao ? `Editar ${catalogKind === "names" ? "nome" : "categoria"}` : `Adicionar ${catalogKind === "names" ? "nome" : "categoria"}`}</h4>
          </div>
          <button className="close-editor" type="button" aria-label="Fechar editor" onClick={fecharEditor}>×</button>
        </div>
        <label>
          <span>{catalogKind === "names" ? "Nome do serviço" : "Nome da categoria"}</span>
          <input value={nomeEmEdicao?.nome ?? novoNome} onChange={(event) => nomeEmEdicao ? setNomeEmEdicao({ ...nomeEmEdicao, nome: event.target.value }) : setNovoNome(event.target.value)} placeholder={catalogKind === "names" ? "Ex.: Manicure" : "Ex.: Unhas"} required />
        </label>
        {catalogKind === "names" && <div className="tag-editor">
          <span className="tag-label">Categorias</span>
          <div className="tag-list" aria-label="Categorias selecionadas">
            {categoriaIdsEmEdicao.map((categoriaId) => {
              const categoria = categorias.find((item) => item.id === categoriaId);
              return categoria ? <button className="catalog-tag selected" type="button" key={categoria.id} onClick={() => alternarCategoria(categoria.id)} title={`Remover ${categoria.nome}`}>{categoria.nome}<X size={12} /></button> : null;
            })}
            {!categoriaIdsEmEdicao.length && <span className="tag-empty">Nenhuma categoria selecionada</span>}
          </div>
          <div className="tag-options" aria-label="Adicionar categoria">
            {categorias.filter((categoria) => !categoriaIdsEmEdicao.includes(categoria.id)).map((categoria) => <button className="catalog-tag option" type="button" key={categoria.id} onClick={() => alternarCategoria(categoria.id)}>+ {categoria.nome}</button>)}
          </div>
        </div>}
        <div className="editor-actions">
          <button className="icon-action save-action" type="submit" disabled={salvando} title={nomeEmEdicao ? "Atualizar nome" : "Adicionar nome"} aria-label={nomeEmEdicao ? "Atualizar nome" : "Adicionar nome"}><Save size={17} /></button>
          <button className="icon-action cancel-action" type="button" onClick={fecharEditor} title="Cancelar" aria-label="Cancelar"><X size={17} /></button>
        </div>
      </form>
    );
  }

  function renderPaginacao() {
    if (carregando || !nomesFiltrados.length) return null;
    return (
      <div className="catalog-pagination">
        <span className="catalog-range">{primeiroRegistro + 1}–{ultimoRegistro} de {nomesFiltrados.length}</span>
        <div className="page-buttons">
          <button type="button" disabled={paginaSegura === 1} onClick={() => setPaginaAtual(1)} aria-label="Primeira página" title="Primeira página"><ChevronsLeft size={15} /></button>
          <button type="button" disabled={paginaSegura === 1} onClick={() => setPaginaAtual((pagina) => pagina - 1)} aria-label="Página anterior" title="Página anterior"><ChevronLeft size={15} /></button>
          {Array.from({ length: totalPaginas }, (_, index) => index + 1).map((pagina) => <button className={pagina === paginaSegura ? "page-button active" : "page-button"} type="button" key={pagina} onClick={() => setPaginaAtual(pagina)} aria-current={pagina === paginaSegura ? "page" : undefined}>{pagina}</button>)}
          <button type="button" disabled={paginaSegura === totalPaginas} onClick={() => setPaginaAtual((pagina) => pagina + 1)} aria-label="Próxima página" title="Próxima página"><ChevronRight size={15} /></button>
          <button type="button" disabled={paginaSegura === totalPaginas} onClick={() => setPaginaAtual(totalPaginas)} aria-label="Última página" title="Última página"><ChevronsRight size={15} /></button>
        </div>
      </div>
    );
  }

  const avatarLabel = (userName ?? "Administrador").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");

  return (
    <section className="admin-area" id="administracao" aria-labelledby="admin-title">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-heading">
          <div className="admin-identity">
            <div className="admin-avatar-menu">
              <button className="user-avatar" type="button" aria-label="Abrir menu da conta" aria-expanded={accountMenuOpen} onClick={() => setAccountMenuOpen((open) => !open)}>{avatarLabel}</button>
              {accountMenuOpen && <div className="avatar-popover admin-avatar-popover"><span>{userName}</span><button className="popover-action" type="button" onClick={() => void logout()}>Sair</button></div>}
            </div>
            <p className="eyebrow">Administração</p>
          </div>
          <h2 id="admin-title">Agenda</h2>
        </div>
        <nav className="admin-nav" aria-label="Menu administrativo">
          <button className={section === "overview" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("overview")}>Visão geral</button>
          <p className="admin-nav-label">Catálogos</p>
          <button className={section === "catalog" && catalogKind === "names" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => { setCatalogKind("names"); setSection("catalog"); }}>Nomes de Serviço</button>
          <button className={section === "catalog" && catalogKind === "categories" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => { setCatalogKind("categories"); setSection("catalog"); }}>Categorias</button>
          <button className={section === "catalog" && catalogKind === "specialties" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => { setCatalogKind("specialties"); setSection("catalog"); }}>Especialidades</button>
          <button className="admin-nav-item muted" type="button" disabled>Tipos de procedimento</button>
          <p className="admin-nav-label">Operação</p>
          <button className={section === "users" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("users")}>Usuários</button>
          <button className={section === "organizations" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("organizations")}>Organizações</button>
          <button className={section === "professionals" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("professionals")}>Profissionais</button>
          <button className={section === "territorial" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("territorial")}>Território</button>
          <button className="admin-nav-item muted" type="button" disabled>Permissões</button>
        </nav>
      </aside>
      <div className="admin-content">
        {section === "overview" && <header className="admin-heading">
          <div>
            <p className="eyebrow">Administração da plataforma</p>
            <div className="admin-title-line">
              <h2>Visão geral</h2>
            </div>
            <p className="admin-copy">Acompanhe os recursos centrais da plataforma.</p>
          </div>
          <span className="admin-badge">Administrador</span>
        </header>}
        {section === "overview" && <div className="admin-overview">
          <div className="admin-stat-grid">
            <article className="admin-stat"><span className="admin-stat-label">Nomes de Serviço</span><strong>{carregando ? "-" : nomes.length}</strong><button className="text-button" type="button" onClick={() => { setCatalogKind("names"); setSection("catalog"); }}>Abrir catálogo</button></article>
            <article className="admin-stat"><span className="admin-stat-label">Categorias</span><strong>{categorias.length || "-"}</strong><button className="text-button" type="button" onClick={() => { setCatalogKind("categories"); setSection("catalog"); }}>Abrir catálogo</button></article>
            <article className="admin-stat"><span className="admin-stat-label">Especialidades</span><strong>{especialidades.length || "-"}</strong><button className="text-button" type="button" onClick={() => { setCatalogKind("specialties"); setSection("catalog"); }}>Abrir catálogo</button></article>
          </div>
          <div className="admin-welcome"><p className="eyebrow">Próximo passo</p><h3>Organize os catálogos da plataforma.</h3><p>Use o menu lateral para manter os dados compartilhados por profissionais e clientes.</p><button type="button" onClick={() => setSection("catalog")}>Gerenciar nomes de serviço</button></div>
        </div>}
        {section === "users" && <div className="catalog-panel">
          <div className="catalog-heading"><div><h3>Usuários</h3></div><div className="catalog-heading-actions"><span className="result-count">{usuarios.length} item{usuarios.length === 1 ? "" : "s"}</span><button className="icon-action add-icon" type="button" onClick={abrirNovoUsuario}><Plus size={20} /></button></div></div>
          {erro && <p className="toast-message error" role="alert">{erro}</p>}
          {mensagem && <p className="toast-message success" role="status">{mensagem}</p>}
          {formUsuarioAberto && <form className="catalog-editor catalog-editor-full" onSubmit={salvarUsuario}>
            <div className="editor-heading">
              <div><p className="eyebrow">{usuarioEmEdicao ? "Edição" : "Novo registro"}</p><h4>{usuarioEmEdicao ? "Editar usuário" : "Adicionar usuário"}</h4></div>
              <button className="close-editor" type="button" aria-label="Fechar editor" onClick={() => setFormUsuarioAberto(false)}>×</button>
            </div>
            <label><span>Nome</span><input value={usuarioForm.nome} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, nome: event.target.value }))} required /></label>
            <label><span>Provider</span><input value={usuarioForm.provider} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, provider: event.target.value }))} required /></label>
            <label><span>Subject</span><input value={usuarioForm.subject} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, subject: event.target.value }))} required /></label>
            <label><span>CPF</span><input value={usuarioForm.cpf} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, cpf: event.target.value }))} placeholder="00000000000" /></label>
            <label><span>E-mail</span><input type="email" value={usuarioForm.email} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, email: event.target.value }))} /></label>
            <label><span>Telefone</span><input value={usuarioForm.telefone} onChange={(event) => setUsuarioForm((atual) => ({ ...atual, telefone: event.target.value }))} /></label>
            <div className="editor-actions"><button className="icon-action save-action" type="submit"><Save size={17} /></button><button className="icon-action cancel-action" type="button" onClick={() => setFormUsuarioAberto(false)}><X size={17} /></button></div>
          </form>}
          {!formUsuarioAberto && <div className="catalog-table" role="table" aria-label="Usuários">
            <div className="catalog-table-header"><span>Nome</span><span>Contato</span><span>Provider</span><span>Ações</span></div>
            {usuarios.map((usuario) => (
              <div className="catalog-row user-row" role="row" key={usuario.id}>
                <div className="catalog-name-cell"><span role="cell">{usuario.nome}</span></div>
                <div className="catalog-name-cell"><span role="cell">{usuario.email ?? usuario.telefone ?? "—"}</span></div>
                <div className="catalog-name-cell"><span role="cell">{usuario.provider}</span></div>
                <div className="row-actions" role="cell"><button className="icon-action subtle" type="button" onClick={() => abrirEdicaoUsuario(usuario)}><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" onClick={() => void removerUsuario(usuario.id)}><Trash2 size={15} /></button></div>
              </div>
            ))}
            {!usuarios.length && <p className="message">Nenhum usuário cadastrado.</p>}
          </div>}
        </div>}
        {section === "organizations" && <div className="catalog-panel">
          <div className="catalog-heading"><div><h3>Organizações</h3></div><div className="catalog-heading-actions"><span className="result-count">{organizacoes.length} item{organizacoes.length === 1 ? "" : "s"}</span><button className="icon-action add-icon" type="button" onClick={abrirNovaOrganizacao}><Plus size={20} /></button></div></div>
          {erro && <p className="toast-message error" role="alert">{erro}</p>}
          {mensagem && <p className="toast-message success" role="status">{mensagem}</p>}
          {formOrganizacaoAberto && <form className="catalog-editor catalog-editor-full organization-editor" onSubmit={salvarOrganizacao}>
            <div className="editor-heading"><div><h4>{organizacaoEmEdicao ? "Editar organização" : "Adicionar organização"}</h4></div><button className="close-editor" type="button" onClick={() => setFormOrganizacaoAberto(false)}>×</button></div>
            <div className="organization-tabs"><button type="button" className={organizacaoTab === "dados" ? "organization-tab active" : "organization-tab"} onClick={() => setOrganizacaoTab("dados")}>Dados gerais</button><button type="button" className={organizacaoTab === "enderecos" ? "organization-tab active" : "organization-tab"} onClick={() => setOrganizacaoTab("enderecos")}>Endereços</button></div>
            {organizacaoTab === "dados" && <>
            <div className="editor-section-title"><span>Identidade</span><small>Como a organização aparece na plataforma</small></div>
            <div className="editor-field-wide"><label><span>Nome legal</span><input value={organizacaoForm.nome} onChange={(event) => setOrganizacaoForm((atual) => ({ ...atual, nome: event.target.value }))} required /></label></div>
            <div className="editor-field-wide"><label><span>Nome de fantasia <small>(opcional)</small></span><input value={organizacaoForm.nome_fantasia} onChange={(event) => setOrganizacaoForm((atual) => ({ ...atual, nome_fantasia: event.target.value }))} /></label></div>
            <label><span>CNPJ <small>(opcional)</small></span><input value={formatarCnpj(organizacaoForm.cnpj)} onChange={(event) => setOrganizacaoForm((atual) => ({ ...atual, cnpj: event.target.value.replace(/\D/g, "").slice(0, 14) }))} placeholder="00.000.000/0000-00" inputMode="numeric" /></label>
            <label><span>Modelo de operação</span><select value={organizacaoForm.unipessoal ? "independente" : "equipe"} onChange={(event) => setOrganizacaoForm((atual) => ({ ...atual, unipessoal: event.target.value === "independente" }))}><option value="equipe">Equipe</option><option value="independente">Independente</option></select></label>
            <div className="editor-section-title"><span>Especialidades</span><small>Serviços que a organização oferece</small></div>
            <div className="tag-editor"><span className="tag-label">Especialidades</span><div className="tag-list">{organizacaoForm.especialidade_ids.map((id) => { const item = especialidadesCatalogo.find((especialidade) => especialidade.id === id); return item ? <button className="catalog-tag selected" key={id} type="button" onClick={() => setOrganizacaoForm((atual) => ({ ...atual, especialidade_ids: atual.especialidade_ids.filter((itemId) => itemId !== id) }))}>{item.nome}<X size={12} /></button> : null; })}{!organizacaoForm.especialidade_ids.length && <span className="tag-empty">Nenhuma especialidade selecionada</span>}</div><div className="tag-options">{especialidadesCatalogo.filter((especialidade) => !organizacaoForm.especialidade_ids.includes(especialidade.id)).map((especialidade) => <button className="catalog-tag option" key={especialidade.id} type="button" onClick={() => setOrganizacaoForm((atual) => ({ ...atual, especialidade_ids: [...atual.especialidade_ids, especialidade.id] }))}>+ {especialidade.nome}</button>)}</div></div>
            </>}
            {organizacaoTab === "enderecos" && <div className="organization-addresses"><div className="organization-address-list">{enderecosOrganizacao.length ? enderecosOrganizacao.map((endereco, index) => <div className="organization-address-item" key={`${endereco.cep}-${index}`}><div><strong>{endereco.descricao ?? "Endereço"}{endereco.principal ? " · Principal" : ""}</strong><span>{endereco.logradouro}, {endereco.numero}</span><small>{endereco.bairro ? `${endereco.bairro} · ` : ""}{endereco.cidade} / {endereco.estado} · {endereco.cep}</small></div></div>) : <p className="tag-empty">Nenhum endereço cadastrado.</p>}</div>{organizacaoEmEdicao ? <>{adicionandoEndereco ? <><EnderecoFields apiFetch={apiFetch} endereco={organizacaoForm} onChange={(patch) => setOrganizacaoForm((atual) => ({ ...atual, ...patch }))} /><label className="principal-address-toggle"><input type="checkbox" checked={novoEnderecoPrincipal} onChange={(event) => setNovoEnderecoPrincipal(event.target.checked)} /> Tornar este o endereço principal</label><div className="address-tab-actions"><button className="icon-action save-action" type="button" onClick={() => void adicionarEnderecoOrganizacao()} title="Salvar endereço" aria-label="Salvar endereço"><Save size={17} /></button><button className="icon-action cancel-action" type="button" onClick={() => setAdicionandoEndereco(false)} title="Cancelar" aria-label="Cancelar"><X size={17} /></button></div></> : <button className="secondary-button address-add-button" type="button" onClick={() => setAdicionandoEndereco(true)}><Plus size={16} /> Adicionar endereço</button>}</> : <p className="address-tab-note">Salve a organização antes de adicionar endereços.</p>}</div>}
            <div className="editor-actions"><button className="icon-action save-action" type="submit"><Save size={17} /></button><button className="icon-action cancel-action" type="button" onClick={() => setFormOrganizacaoAberto(false)}><X size={17} /></button></div>
          </form>}
          {!formOrganizacaoAberto && <div className="catalog-table" role="table" aria-label="Organizações">
            <div className="catalog-table-header"><span>Nome</span><span>Ações</span></div>
            {organizacoes.map((organizacao) => (
              <div className="catalog-row org-row" role="row" key={organizacao.id}>
                <div className="catalog-name-cell"><span role="cell">{organizacao.nome_fantasia || organizacao.nome}</span></div>
                <div className="row-actions" role="cell"><button className="icon-action subtle" type="button" onClick={() => abrirEdicaoOrganizacao(organizacao)}><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" onClick={() => void removerOrganizacao(organizacao.id)}><Trash2 size={15} /></button></div>
              </div>
            ))}
            {!organizacoes.length && <p className="message">Nenhuma organização cadastrada.</p>}
          </div>}
        </div>}
        {section === "professionals" && <div className="catalog-panel">
          <div className="catalog-heading"><div><h3>Profissionais</h3></div><div className="catalog-heading-actions"><span className="result-count">{organizacoes.filter((item) => item.unipessoal).length} item{organizacoes.filter((item) => item.unipessoal).length === 1 ? "" : "s"}</span><button className="icon-action add-icon" type="button" onClick={abrirNovoProfissional}><Plus size={20} /></button></div></div>
          {erro && <p className="toast-message error" role="alert">{erro}</p>}
          {mensagem && <p className="toast-message success" role="status">{mensagem}</p>}
          {formProfissionalAberto && <form className="catalog-editor catalog-editor-full" onSubmit={salvarProfissional}>
            <div className="editor-heading"><div><p className="eyebrow">Novo registro</p><h4>Adicionar profissional independente</h4></div><button className="close-editor" type="button" onClick={() => setFormProfissionalAberto(false)}>×</button></div>
            <label><span>Nome</span><input value={profissionalForm.nome} onChange={(event) => setProfissionalForm((atual) => ({ ...atual, nome: event.target.value }))} required /></label>
            <div className="editor-section-title"><span>Endereço principal</span><small>Comece pelo CEP para preencher os dados automaticamente</small></div>
            <EnderecoFields apiFetch={apiFetch} endereco={profissionalForm} onChange={(patch) => setProfissionalForm((atual) => ({ ...atual, ...patch }))} />
            <div className="tag-editor"><span className="tag-label">Especialidades</span><div className="tag-list">{profissionalForm.especialidade_ids.map((id) => { const item = especialidadesCatalogo.find((especialidade) => especialidade.id === id); return item ? <button className="catalog-tag selected" key={id} type="button" onClick={() => setProfissionalForm((atual) => ({ ...atual, especialidade_ids: atual.especialidade_ids.filter((itemId) => itemId !== id) }))}>{item.nome}<X size={12} /></button> : null; })}{!profissionalForm.especialidade_ids.length && <span className="tag-empty">Nenhuma especialidade selecionada</span>}</div><div className="tag-options">{especialidadesCatalogo.filter((especialidade) => !profissionalForm.especialidade_ids.includes(especialidade.id)).map((especialidade) => <button className="catalog-tag option" key={especialidade.id} type="button" onClick={() => setProfissionalForm((atual) => ({ ...atual, especialidade_ids: [...atual.especialidade_ids, especialidade.id] }))}>+ {especialidade.nome}</button>)}</div></div>
            <div className="editor-actions"><button className="icon-action save-action" type="submit"><Save size={17} /></button><button className="icon-action cancel-action" type="button" onClick={() => setFormProfissionalAberto(false)}><X size={17} /></button></div>
          </form>}
          {!formProfissionalAberto && <div className="catalog-table" role="table" aria-label="Profissionais independentes">
            <div className="catalog-table-header"><span>Nome</span><span>Ações</span></div>
            {organizacoes.filter((item) => item.unipessoal).map((organizacao) => (
              <div className="catalog-row prof-row" role="row" key={organizacao.id}>
                <div className="catalog-name-cell"><span role="cell">{organizacao.nome_fantasia || organizacao.nome}</span></div>
                <div className="row-actions" role="cell"><button className="icon-action subtle" type="button" onClick={() => abrirEdicaoOrganizacao(organizacao)}><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" onClick={() => void removerOrganizacao(organizacao.id)}><Trash2 size={15} /></button></div>
              </div>
            ))}
            {!organizacoes.some((item) => item.unipessoal) && <p className="message">Nenhum profissional independente cadastrado.</p>}
          </div>}
        </div>}
        {section === "territorial" && <div className="catalog-panel">
          <div className="catalog-heading"><div><p className="eyebrow">Catálogo territorial</p><h3>Território</h3></div></div>
          <TerritorialAdmin apiFetch={apiFetch} apiUrl={apiUrl} />
        </div>}
        {section === "catalog" && <div className="catalog-panel">
          <div className="catalog-heading"><div><h3>{catalogTitle}</h3></div><div className="catalog-heading-actions"><span className="result-count">{nomes.length} item{nomes.length === 1 ? "" : "s"}</span><button className={buscaOpen ? "icon-action search-icon active-icon" : "icon-action search-icon"} type="button" title={`Buscar ${catalogLabel}`} aria-label={`Buscar ${catalogLabel}`} aria-pressed={buscaOpen} onClick={() => setBuscaOpen((open) => !open)}><Search size={19} /></button><button className="icon-action add-icon" type="button" title={`Nova ${catalogKind === "names" ? "nome de serviço" : "categoria"}`} aria-label={`Nova ${catalogKind === "names" ? "nome de serviço" : "categoria"}`} onClick={abrirNovoNome}><Plus size={20} strokeWidth={2} /></button></div></div>
          {!editorOpen && buscaOpen && <div className="catalog-toolbar"><label htmlFor="buscar-nome-servico">Buscar</label><input id="buscar-nome-servico" value={termoBusca} onChange={(event) => { setTermoBusca(event.target.value); setPaginaAtual(1); }} placeholder={`Filtrar ${catalogLabel}`} autoFocus /><span className="catalog-range">{nomesFiltrados.length ? `${primeiroRegistro + 1}–${ultimoRegistro} de ${nomesFiltrados.length}` : "0 de 0"}</span></div>}
          {!editorOpen && nomesSelecionadosLista.length > 0 && <div className="selection-toolbar"><span>{nomesSelecionadosLista.length} selecionado{nomesSelecionadosLista.length === 1 ? "" : "s"}</span><button className="icon-action subtle" type="button" title="Editar registro selecionado" aria-label="Editar registro selecionado" disabled={nomesSelecionadosLista.length !== 1} onClick={() => { const nome = nomesSelecionadosLista[0]; if (nome) abrirEdicao(nome); }}><Pencil size={16} /></button><button className="icon-action danger-icon" type="button" title="Excluir registros selecionados" aria-label="Excluir registros selecionados" onClick={() => void removerSelecionados()}><Trash2 size={16} /></button></div>}
          {erro && <p className="toast-message error" role="alert">{erro}</p>}
          {mensagem && <p className="toast-message success" role="status">{mensagem}</p>}
          {editorOpen ? renderEditor() : <div className="catalog-workspace">
            <div>
              {carregando && <p className="message">Carregando catálogo...</p>}
              {!carregando && nomes.length === 0 && <p className="message">Nenhum nome de serviço cadastrado.</p>}
              {!carregando && nomesFiltrados.length === 0 && nomes.length > 0 && <p className="message">Nenhum nome corresponde à busca.</p>}
              {renderPaginacao()}
              {!carregando && nomesFiltrados.length > 0 && <div className="catalog-table" role="table" aria-label={catalogTitle}><div className="catalog-table-header"><div className="selection-shortcuts"><button type="button" onClick={selecionarTodos}>Todos</button><button type="button" onClick={selecionarNenhum}>Nenhum</button><button type="button" onClick={inverterSelecao}>Inverter seleção</button></div><span>{nomesSelecionadosLista.length ? `${nomesSelecionadosLista.length} selecionado${nomesSelecionadosLista.length === 1 ? "" : "s"}` : ""}</span></div>{nomesDaPagina.map((nome) => <div className={nomesSelecionados.has(nome.id) ? "catalog-row selected" : "catalog-row"} role="row" key={nome.id}><label><input type="checkbox" checked={nomesSelecionados.has(nome.id)} onChange={() => alternarSelecao(nome)} aria-label={`Selecionar ${nome.nome}`} /></label><div className="catalog-name-cell"><span role="cell">{nome.nome}</span>{catalogKind === "names" && <div className="tag-list row-tags">{nome.categorias?.map((categoria) => <span className="catalog-tag" key={categoria.id}>{categoria.nome}</span>)}</div>}</div><div className="row-actions" role="cell"><button className="icon-action subtle" type="button" title={`Editar ${catalogLabel}`} aria-label={`Editar ${catalogLabel}`} disabled={nomesSelecionados.size > 1} onClick={() => abrirEdicao(nome)}><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" title={`Remover ${catalogLabel}`} aria-label={`Remover ${catalogLabel}`} onClick={() => void removerNome(nome)}><Trash2 size={15} /></button></div></div>)}</div>}
              {renderPaginacao()}
            </div>
          </div>}
        </div>}
      </div>
      {exclusaoPendente && <div className="confirm-backdrop" role="presentation" onClick={() => setExclusaoPendente(null)}>
        <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title" onClick={(event) => event.stopPropagation()}>
          <div className="attention-icon" aria-hidden="true">!</div>
          <div className="confirm-content">
            <h3 id="confirm-title">Confirmar exclusão</h3>
            <p>{exclusaoPendente.length === 1 ? `O nome “${exclusaoPendente[0].nome}” será removido.` : `${exclusaoPendente.length} nomes de serviço serão removidos.`}</p>
            <span>Essa ação não poderá ser desfeita.</span>
          </div>
          <div className="confirm-actions">
            <button className="secondary-button" type="button" onClick={() => setExclusaoPendente(null)}>Cancelar</button>
            <button className="danger-button" type="button" onClick={() => void confirmarExclusao()}>Excluir</button>
          </div>
        </div>
      </div>}
    </section>
  );
}
