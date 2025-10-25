import type { ButtonHTMLAttributes, DetailedHTMLProps } from "react";

export type ButtonProps = DetailedHTMLProps<
  ButtonHTMLAttributes<HTMLButtonElement>,
  HTMLButtonElement
> & {
  variant?: "primary" | "secondary" | "ghost";
};

export function Button({ variant = "primary", ...props }: ButtonProps) {
  const classes = [
    "inline-flex items-center justify-center rounded-md border text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
  ];

  switch (variant) {
    case "secondary":
      classes.push(
        "border-transparent bg-gray-100 text-gray-900 hover:bg-gray-200",
      );
      break;
    case "ghost":
      classes.push("border-transparent text-gray-700 hover:bg-gray-50");
      break;
    default:
      classes.push(
        "border-transparent bg-blue-600 text-white hover:bg-blue-700",
      );
      break;
  }

  return <button className={classes.join(" ")} {...props} />;
}
