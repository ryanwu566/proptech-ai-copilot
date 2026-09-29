import { cloneElement, isValidElement, useId, type InputHTMLAttributes, type ReactElement, type ReactNode, type SelectHTMLAttributes } from "react";
import { joinClassNames } from "./types";

type ControlProps = {
  id?: string;
  className?: string;
  required?: boolean;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
  "aria-required"?: boolean | "true" | "false";
};

export function Field({
  label,
  helperText,
  errorText,
  required,
  optionalText = "選填",
  children,
  className,
}: {
  label: ReactNode;
  helperText?: ReactNode;
  errorText?: ReactNode;
  required?: boolean;
  optionalText?: ReactNode;
  children: ReactElement<ControlProps>;
  className?: string;
}) {
  const generatedId = useId();
  const controlId = children.props.id ?? `${generatedId}-control`;
  const helperId = helperText ? `${generatedId}-helper` : undefined;
  const errorId = errorText ? `${generatedId}-error` : undefined;
  const describedBy = [children.props["aria-describedby"], helperId, errorId].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children, {
      id: controlId,
      required: required || children.props.required,
      "aria-required": required ? true : children.props["aria-required"],
      "aria-describedby": describedBy,
      "aria-invalid": errorText ? true : children.props["aria-invalid"],
    })
    : children;

  return (
    <div className={joinClassNames("ds-field", className)}>
      <div className="ds-field__heading">
        <label className="text-label" htmlFor={controlId}>{label}{required && <span aria-hidden="true"> *</span>}</label>
        {!required && optionalText && <span className="ds-field__optional">（{optionalText}）</span>}
      </div>
      {control}
      {helperText && <div id={helperId} className="text-helper">{helperText}</div>}
      {errorText && <div id={errorId} className="text-helper ds-role-error" role="alert">{errorText}</div>}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={joinClassNames("ds-control", className)} {...props} />;
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={joinClassNames("ds-control", className)} {...props}>{children}</select>;
}

export function UnitInput({
  prefix,
  suffix,
  unitLabel,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { prefix?: ReactNode; suffix?: ReactNode; unitLabel: string }) {
  const unitDescriptionId = `${useId()}-unit`;
  const { "aria-describedby": existingDescription, ...inputProps } = props;
  const describedBy = [existingDescription, unitDescriptionId].filter(Boolean).join(" ");
  return (
    <div className={joinClassNames("ds-unit-input", className)}>
      {prefix && <span className="ds-unit-input__adornment" aria-hidden="true">{prefix}</span>}
      <input className="ds-control ds-numeric" aria-describedby={describedBy} {...inputProps} />
      {suffix && <span className="ds-unit-input__adornment" aria-hidden="true">{suffix}</span>}
      <span id={unitDescriptionId} className="ds-visually-hidden">{unitLabel}</span>
    </div>
  );
}
