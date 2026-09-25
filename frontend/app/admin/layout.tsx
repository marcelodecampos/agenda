"use client";

import { Refine } from "@refinedev/core";
import type { ReactNode } from "react";

const resources = [
  { name: "genders", list: "/admin/genders" },
  { name: "persons", list: "/admin/people" },
  { name: "companies", list: "/admin/people" },
  { name: "federative-units", list: "/admin/localities" },
  { name: "municipalities", list: "/admin/localities" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <Refine resources={resources}>{children}</Refine>;
}
