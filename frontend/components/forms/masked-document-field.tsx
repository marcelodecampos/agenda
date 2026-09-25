"use client";

import type { ChangeEvent } from "react";

type MaskedDocumentFieldProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
};

export function formatCpf(value: string | null | undefined): string {
  const digits = (value ?? "").replace(/\D/g, "").slice(0, 11);
  return digits.replace(/^(\d{3})(\d)/, "$1.$2").replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3").replace(/^(\d{3})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3-$4");
}

export function formatCnpj(value: string | null | undefined): string {
  const digits = (value ?? "").replace(/\D/g, "").slice(0, 14);
  return digits.replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3").replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3/$4").replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, "$1.$2.$3/$4-$5");
}

function MaskedDocumentField({ id, value, onChange, required, disabled, kind }: MaskedDocumentFieldProps & { kind: "cpf" | "cnpj" }) {
  const formatted = kind === "cpf" ? formatCpf(value) : formatCnpj(value);
  const label = kind === "cpf" ? "CPF" : "CNPJ";
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => onChange(kind === "cpf" ? formatCpf(event.target.value) : formatCnpj(event.target.value));
  return <label id={`${id}-field`} htmlFor={id}><span>{label}</span><input id={id} className={kind === "cpf" ? "masked-cpf-input" : "masked-cnpj-input"} required={required} disabled={disabled} value={formatted} onChange={handleChange} /></label>;
}

export function CpfField(props: MaskedDocumentFieldProps) { return <MaskedDocumentField {...props} kind="cpf" />; }
export function CnpjField(props: MaskedDocumentFieldProps) { return <MaskedDocumentField {...props} kind="cnpj" />; }
