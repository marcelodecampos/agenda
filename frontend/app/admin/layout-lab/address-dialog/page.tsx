"use client";

import { Button, Form, Input, Modal, Select, Typography, message } from "antd";
import { useState } from "react";

import { AdminSidebar } from "@/components/admin/admin-sidebar";

const federativeUnits = ["AC - Acre", "AL - Alagoas", "AP - Amapá", "AM - Amazonas", "BA - Bahia", "CE - Ceará", "DF - Distrito Federal", "ES - Espírito Santo", "GO - Goiás", "MA - Maranhão", "MT - Mato Grosso", "MS - Mato Grosso do Sul", "MG - Minas Gerais", "PA - Pará", "PB - Paraíba", "PR - Paraná", "PE - Pernambuco", "PI - Piauí", "RJ - Rio de Janeiro", "RN - Rio Grande do Norte", "RS - Rio Grande do Sul", "RO - Rondônia", "RR - Roraima", "SC - Santa Catarina", "SP - São Paulo", "SE - Sergipe", "TO - Tocantins"];

export default function AddressDialogPage() {
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  function submitAddress(values: Record<string, string>) {
    void values;
    setOpen(false);
    form.resetFields();
    messageApi.success("Exemplo validado localmente; nenhum dado foi salvo.");
  }

  const groups = [{ id: "address-dialog-group-tables", label: "Tabelas", items: [{ id: "address-dialog-nav-gender", label: "Gênero", href: "/admin/genders" }, { id: "address-dialog-nav-locality", label: "Localidade", href: "/admin/localities" }] }, { id: "address-dialog-group-people", label: "Pessoa", items: [{ id: "address-dialog-nav-person", label: "Pessoa física", href: "/admin/people" }, { id: "address-dialog-nav-company", label: "Pessoa jurídica", href: "/admin/people" }] }, { id: "address-dialog-group-layout", label: "Elementos de layout", items: [{ id: "address-dialog-nav-buttons", label: "Botões", href: "/admin/button-lab" }, { id: "address-dialog-nav-address", label: "Diálogo de endereço", href: "/admin/layout-lab/address", active: true }] }];

  return <main id="address-dialog-page" className="admin-area">{contextHolder}<AdminSidebar id="address-dialog-sidebar" groups={groups} /><section id="address-dialog-content" className="admin-content"><Typography.Title id="address-dialog-title" level={2}>Diálogo de endereço</Typography.Title><Typography.Paragraph id="address-dialog-description" type="secondary">Exemplo de usabilidade. Os dados não são persistidos.</Typography.Paragraph><Button id="address-dialog-open" type="primary" onClick={() => setOpen(true)}>Incluir endereço</Button><Modal title="Incluir endereço" open={open} onCancel={() => setOpen(false)} footer={null} destroyOnHidden modalRender={(node) => <div id="address-dialog-modal">{node}</div>}><Form id="address-dialog-form" form={form} layout="vertical" onFinish={submitAddress}><Form.Item id="address-dialog-postal-code-item" label="CEP" name="postal_code" rules={[{ required: true, message: "Informe o CEP." }]}><Input id="address-dialog-postal-code" placeholder="00000-000" /></Form.Item><Form.Item id="address-dialog-street-item" label="Logradouro" name="street_name" rules={[{ required: true, message: "Informe o logradouro." }]}><Input id="address-dialog-street" /></Form.Item><Form.Item id="address-dialog-number-item" label="Número" name="number" rules={[{ required: true, message: "Informe o número." }]}><Input id="address-dialog-number" /></Form.Item><Form.Item id="address-dialog-complement-item" label="Complemento" name="complement"><Input id="address-dialog-complement" /></Form.Item><Form.Item id="address-dialog-neighborhood-item" label="Bairro" name="neighborhood"><Input id="address-dialog-neighborhood" /></Form.Item><Form.Item id="address-dialog-state-item" label="UF" name="state" rules={[{ required: true, message: "Selecione a UF." }]}><Select id="address-dialog-state" options={federativeUnits.map((unit) => ({ value: unit, label: unit }))} /></Form.Item><Form.Item id="address-dialog-city-item" label="Município" name="municipality" rules={[{ required: true, message: "Informe o município." }]}><Input id="address-dialog-city" /></Form.Item><Form.Item id="address-dialog-actions-item"><Button id="address-dialog-cancel" onClick={() => setOpen(false)}>Cancelar</Button><Button id="address-dialog-submit" type="primary" htmlType="submit">Validar endereço</Button></Form.Item></Form></Modal></section></main>;
}
