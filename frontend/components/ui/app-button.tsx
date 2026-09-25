import type { ReactNode } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AppButtonProps = ButtonProps;

export function AppButton({ className, children, ...props }: AppButtonProps) {
  return (
    <Button className={cn("app-button", className)} {...props}>
      {children}
    </Button>
  );
}

export type AppIconButtonProps = Omit<AppButtonProps, "size"> & {
  size?: "icon";
  children: ReactNode;
};

export function AppIconButton({ className, children, ...props }: AppIconButtonProps) {
  return (
    <AppButton className={cn("app-icon-button", className)} size="icon" {...props}>
      {children}
    </AppButton>
  );
}
