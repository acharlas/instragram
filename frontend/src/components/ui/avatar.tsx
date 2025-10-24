import type { ComponentPropsWithoutRef } from "react";

export function Avatar({ children, ...props }: ComponentPropsWithoutRef<"div">) {
  return (
    <div aria-live="polite" {...props}>
      {children}
    </div>
  );
}

export function AvatarImage(props: ComponentPropsWithoutRef<"img">) {
  return <img {...props} alt={props.alt ?? ""} />;
}

export function AvatarFallback({ children, ...props }: ComponentPropsWithoutRef<"span">) {
  return (
    <span role="img" aria-label="avatar fallback" {...props}>
      {children}
    </span>
  );
}
