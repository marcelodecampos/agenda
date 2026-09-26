"use client";

import { Layout, Menu, Typography } from "antd";
import type { MenuProps } from "antd";
import { useState } from "react";

type AdminNavItem = { id: string; label: string; href?: string; active?: boolean; onClick?: () => void };
type AdminNavGroup = { id: string; label: string; items: AdminNavItem[] };
type AdminSidebarProps = { id: string; groups: AdminNavGroup[] };

// Itens exibidos em todas as telas, mesmo quando a página não os declara.
const requiredItems: Record<string, { key: string; label: string; href: string }[]> = {
  Tabelas: [{ key: "localities", label: "Localidade", href: "/admin/localities" }],
  "Elementos de layout": [
    { key: "layout-lab", label: "Laboratório de layout", href: "/admin/layout-lab" },
    { key: "address-dialog", label: "Diálogo de endereço", href: "/admin/layout-lab/address-dialog" },
    { key: "municipality-search", label: "Consulta de município", href: "/admin/layout-lab/municipality-search" },
  ],
};

export function AdminSidebar({ id, groups }: AdminSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navigationGroups = groups.map((group): AdminNavGroup => {
    const missing = (requiredItems[group.label] ?? []).filter((required) => !group.items.some((item) => item.href === required.href));
    return { ...group, items: [...group.items, ...missing.map((required) => ({ id: `${id}-nav-${required.key}`, label: required.label, href: required.href }))] };
  });
  const items: MenuProps["items"] = navigationGroups.map((group) => ({ key: group.id, label: group.label, children: group.items.map((item) => ({ key: item.id, label: <a id={`${item.id}-link`} href={item.href ?? "#"} onClick={(event) => { if (item.onClick) { event.preventDefault(); item.onClick(); } }}>{item.label}</a> })) }));
  const selectedKeys = navigationGroups.flatMap((group) => group.items.filter((item) => item.active).map((item) => item.id));
  return <Layout.Sider id={id} collapsible collapsed={collapsed} onCollapse={setCollapsed} width={218} collapsedWidth={64} theme="dark"><div id={`${id}-brand`} style={{ padding: "24px 16px", color: "#fff" }}><Typography.Text style={{ color: "#9cc3df", fontWeight: 800 }}>agenda.</Typography.Text>{!collapsed && <Typography.Title level={4} style={{ color: "#fff", margin: "8px 0 0" }}>Administração</Typography.Title>}</div><Menu id={`${id}-menu`} theme="dark" mode="inline" items={items} selectedKeys={selectedKeys} /></Layout.Sider>;
}
