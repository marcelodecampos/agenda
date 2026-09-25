"use client";

import { App as AntdApp, ConfigProvider } from "antd";
import type { ReactNode } from "react";
import ptBR from "antd/locale/pt_BR";

export function AntdProvider({ children }: { children: ReactNode }) {
  return <ConfigProvider locale={ptBR} theme={{ token: { fontFamily: "inherit", borderRadius: 0, colorPrimary: "#286887", controlHeight: 32 } }}><AntdApp>{children}</AntdApp></ConfigProvider>;
}
