import { useEffect, useId, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  description: string;
  cancelLabel?: string;
  confirmLabel?: string;
  confirmVariant?: "default" | "destructive";
  warning?: string;
  error?: string;
  busy?: boolean;
  busyLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  cancelLabel = "Continuar aqui",
  confirmLabel = "Sair",
  confirmVariant = "default",
  warning,
  error,
  busy = false,
  busyLabel = "Processando...",
  onCancel,
  onConfirm,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCancelRef = useRef(onCancel);
  const busyRef = useRef(busy);
  const titleId = useId();
  const descriptionId = useId();
  const warningId = useId();
  const errorId = useId();
  onCancelRef.current = onCancel;
  busyRef.current = busy;

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busyRef.current) onCancelRef.current();
      if (event.key === "Tab") {
        const active = document.activeElement;
        if (event.shiftKey && active === cancelRef.current) {
          event.preventDefault();
          confirmRef.current?.focus();
        } else if (!event.shiftKey && active === confirmRef.current) {
          event.preventDefault();
          cancelRef.current?.focus();
        }
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open) return null;
  const describedBy = [descriptionId, warning ? warningId : "", error ? errorId : ""].filter(Boolean).join(" ");
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
    <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={describedBy}>
      <h2 id={titleId}>{title}</h2>
      <p id={descriptionId}>{description}</p>
      {warning && <p className="confirm-dialog-warning" id={warningId}>{warning}</p>}
      {error && <p className="confirm-dialog-error" id={errorId} role="alert">{error}</p>}
      <div className="dialog-actions">
        <button ref={cancelRef} className="btn secondary-btn" type="button" onClick={onCancel} disabled={busy}>{cancelLabel}</button>
        <button ref={confirmRef} className={`btn ${confirmVariant === "destructive" ? "dialog-destructive" : ""}`} type="button" onClick={onConfirm} disabled={busy}>{busy ? busyLabel : confirmLabel}</button>
      </div>
    </section>
  </div>;
}
