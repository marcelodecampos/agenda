import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./auth-provider";
import { AntdProvider } from "./antd-provider";

export const metadata: Metadata = {
  title: "agenda. | Encontre seu próximo cuidado",
  description: "Descubra serviços de beleza, saúde e bem-estar perto de você.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR">
      <body>
        <AntdProvider><AuthProvider>{children}</AuthProvider></AntdProvider>
      </body>
    </html>
  );
}
