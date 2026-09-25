"use client";

import { Layout } from "antd";
import type { ReactNode } from "react";

import { AdminSidebar } from "@/components/admin/admin-sidebar";

type AdminLayoutProps = {
  id: string;
  groups: Parameters<typeof AdminSidebar>[0]["groups"];
  children: ReactNode;
};

export function AdminLayout({ id, groups, children }: AdminLayoutProps) {
  return <Layout id={id} style={{ minHeight: "100vh", background: "#f3f7fb" }}><AdminSidebar id={`${id}-sidebar`} groups={groups} /><Layout.Content id={`${id}-content`} style={{ minWidth: 0, padding: 28 }}>{children}</Layout.Content></Layout>;
}
