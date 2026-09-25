import { Button as AntButton } from "antd";
import type { ButtonProps as AntButtonProps } from "antd";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "default" | "outline" | "ghost" | "success" | "danger";
export type ButtonSize = "default" | "icon";

export interface ButtonProps extends Omit<AntButtonProps, "type" | "size" | "danger" | "variant"> {
  id: string;
  type?: ButtonHTMLAttributes<HTMLButtonElement>["type"];
  variant?: ButtonVariant;
  size?: ButtonSize;
  children?: ReactNode;
}

export function Button({ id, type = "button", variant = "default", size = "default", children, style, ...props }: ButtonProps) {
  const visualType = variant === "default" ? "primary" : variant === "ghost" ? "text" : "default";
  const palette = { outline: "#1e5d7d", success: "#28734b", danger: "#a64b43" }[variant as "outline" | "success" | "danger"];
  return <AntButton id={id} htmlType={type} type={visualType} danger={variant === "danger"} size={size === "icon" ? "small" : "middle"} style={{ color: palette, borderRadius: 0, fontFamily: "inherit", ...(size === "icon" ? { width: 34, height: 34, padding: 0 } : {}), ...style }} {...props}>{children}</AntButton>;
}
