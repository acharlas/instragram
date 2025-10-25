import Image, { type ImageProps } from "next/image";
import type { ComponentPropsWithoutRef } from "react";

export function Avatar({
  children,
  ...props
}: ComponentPropsWithoutRef<"div">) {
  return (
    <div aria-live="polite" {...props}>
      {children}
    </div>
  );
}

export function AvatarImage({ alt, ...props }: ImageProps) {
  return <Image alt={alt ?? ""} {...props} />;
}

export function AvatarFallback({
  children,
  ...props
}: ComponentPropsWithoutRef<"span">) {
  return (
    <span role="img" aria-label="avatar fallback" {...props}>
      {children}
    </span>
  );
}
