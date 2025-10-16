// src/components/PinRoleTable.jsx
import { useMemo } from "react";

/* ────────────────────────── Constants ────────────────────────── */
const ROLES = [
  { value: "input", label: "input" },
  { value: "output", label: "output" },
  { value: "vdd", label: "vdd" },
  { value: "vss", label: "vss" },
];

const DRIVES = [
  { value: "DC", label: "DC" },
  { value: "PULSE", label: "PULSE" },
];

/* ────────────────────────── UI atoms ─────────────────────────── */
function Select({ value, onChange, disabled, children, className = "" }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      disabled={disabled}
      className={[
        "h-9 rounded-lg bg-slate-900/70 border border-slate-700/70",
        "px-2.5 pr-7 text-[13px] leading-9 outline-none",
        "focus:ring-2 focus:ring-sky-600/40 focus:border-sky-600/40",
        disabled ? "opacity-50 cursor-not-allowed" : "hover:border-slate-600",
        "transition-colors",
        className,
      ].join(" ")}
    >
      {children}
    </select>
  );
}

function Num({ value, onChange, placeholder, disabled, className = "" }) {
  return (
    <input
      type="text"
      inputMode="decimal"
      value={value ?? ""}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={[
        "h-9 rounded-lg bg-slate-900/70 border border-slate-700/70",
        "px-2 text-[13px] outline-none font-mono tabular-nums",
        "focus:ring-2 focus:ring-sky-600/40 focus:border-sky-600/40",
        disabled ? "opacity-50 cursor-not-allowed" : "hover:border-slate-600",
        "transition-colors",
        "w-14 md:w-16",
        className,
      ].join(" ")}
    />
  );
}

/* ────────────────────────── Main table ───────────────────────── */
export default function PinRoleTable({ pins, pinRoles, setPinRoles, pulseDefaults }) {
  const rows = useMemo(() => pins || [], [pins]);

  // immutable updates
  const setRole = (pin, role) =>
    setPinRoles((prev) => ({
      ...prev,
      [pin]: {
        role,
        drive: role === "input" ? prev[pin]?.drive || "DC" : undefined,
        params: role === "input" ? prev[pin]?.params || {} : undefined,
      },
    }));

  const setDrive = (pin, drive) =>
    setPinRoles((prev) => ({
      ...prev,
      [pin]: {
        ...(prev[pin] || { role: "input" }),
        drive,
        params: { ...(prev[pin]?.params || {}) },
      },
    }));

  const setParam = (pin, key, val) =>
    setPinRoles((prev) => ({
      ...prev,
      [pin]: {
        ...(prev[pin] || { role: "input", drive: "DC" }),
        params: { ...(prev[pin]?.params || {}), [key]: val },
      },
    }));

  // placeholders reflect current model
  const ph = {
    v1: pulseDefaults?.v1 ?? "0",
    v2: pulseDefaults?.v2 ?? "VDD",
    td: pulseDefaults?.td ?? "0",
    tr: pulseDefaults?.tr ?? "TR",
    tf: pulseDefaults?.tf ?? "TF",
    pw: pulseDefaults?.pw ?? "PW",
    per: pulseDefaults?.per ?? "PER",
  };

  return (
    <div className="rounded-2xl border-[1.5px] border-emerald-500/50 bg-slate-900/40 overflow-hidden">
      {/* top note */}
      <div className="px-4 py-3 text-[13px] text-slate-400">
        <span className="font-medium text-slate-300">Pin configuration</span>
        <span className="mx-2 text-slate-600">•</span>
        VDD/VSS roles are supply tie-offs only. Drives apply only to{" "}
        <span className="font-medium">input</span> pins.
      </div>

      <div className="overflow-x-auto ">
        <table className="min-w-full text-sm">
          {/* width guidance to keep layout steady */}
          <colgroup>
            <col className="w-32 md:w-40" />
            <col className="w-32" />
            <col className="w-32" />
            <col className="w-18" />
            {/* 7 pulse columns (narrower) */}
            <col className="w-16" />
            <col className="w-16" />
            <col className="w-16" />
            <col className="w-16" />
            <col className="w-16" />
            <col className="w-16" />
            <col className="w-16" />
          </colgroup>

          {/* sticky header */}
          <thead className="bg-slate-950/70 backdrop-blur supports-[backdrop-filter]:bg-slate-950/50 sticky top-0 z-10 border-y-[1.5px] border-emerald-500/40">
            {/* Row 1: section labels */}
            <tr className="uppercase tracking-wide text-[11px] text-slate-300/90">
              <th className="text-left px-4 py-2">Pin</th>
              <th className="text-left px-2 py-2">Role</th>
              <th className="text-left px-2 py-2">Drive</th>
             <th className="text-left px-2 py-2">DC</th>
              <th className="text-left px-1 py-2" colSpan={7}>Pulse</th>
            </tr>
            {/* Row 2: individual pulse field labels */}
            <tr className="uppercase tracking-wide text-[11px] text-slate-300/90">
              <th className="px-4 py-1"></th>
              <th className="px-2 py-1"></th>
              <th className="px-2 py-1"></th>
              <th className="px-2 py-1"></th>
              <th className="text-left px-1 py-1">V1</th>
              <th className="text-left px-1 py-1">V2</th>
              <th className="text-left px-1 py-1">TD</th>
              <th className="text-left px-1 py-1">TR</th>
              <th className="text-left px-1 py-1">TF</th>
              <th className="text-left px-1 py-1">PW</th>
              <th className="text-left px-1 py-1">PER</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((pin, i) => {
              const cfg = pinRoles[pin] || {};
              const role = cfg.role || "input";
              const isInput = role === "input";
              const isSupply = role === "vdd" || role === "vss";
              const drive = isInput ? cfg.drive || "DC" : undefined;
              const p = cfg.params || {};
              const showDC = isInput && drive === "DC";
              const showPulse = isInput && drive === "PULSE";

              return (
                <tr
                  key={pin}
                  className={[
                    "border-t border-slate-800/70",
                    i % 2 === 0 ? "bg-slate-900/30" : "bg-slate-900/20",
                    "hover:bg-slate-800/30 transition-colors",
                  ].join(" ")}
                >
                  {/* Pin label */}
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[13px] text-slate-200">{pin}</span>
                      {isSupply && (
                        <span
                          title="Supply pin"
                          className="text-[10px] uppercase tracking-wide bg-amber-500/15 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded"
                        >
                          supply
                        </span>
                      )}
                      {role === "output" && (
                        <span
                          title="Output pin"
                          className="text-[10px] uppercase tracking-wide bg-sky-500/15 text-sky-300 border border-sky-500/30 px-1.5 py-0.5 rounded"
                        >
                          out
                        </span>
                      )}
                          {role === "input" && (
      <span
        title="Input pin"
        className="text-[10px] uppercase tracking-wide bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded"
      >
        in
      </span>
    )}
                    </div>
                  </td>

                  {/* Role */}
                  <td className="px-2 py-2">
                    <Select value={role} onChange={(v) => setRole(pin, v)}>
                      {ROLES.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </Select>
                  </td>

                  {/* Drive (inputs only) */}
                  <td className="px-2 py-2">
                    <Select
                      value={drive || "DC"}
                      onChange={(v) => setDrive(pin, v)}
                      disabled={!isInput}
                    >
                      {DRIVES.map((d) => (
                        <option key={d.value} value={d.value}>
                          {d.label}
                        </option>
                      ))}
                    </Select>
                  </td>

                  {/* DC */}
                  <td className="px-2 py-2">
                    {showDC ? (
                      <Num value={p.dc} onChange={(v) => setParam(pin, "dc", v)} placeholder="0" />
                    ) : (
                      <div className="h-9" />
                    )}
                  </td>

                  {/* PULSE fields */}
                  {["v1", "v2", "td", "tr", "tf", "pw", "per"].map((k) => (
                    <td key={k} className="px-[4px] py-2 text-left">
                      {showPulse ? (
                        <Num
                          value={p[k]}
                          onChange={(v) => setParam(pin, k, v)}
                          placeholder={ph[k]}
                        />
                      ) : (
                        <div className="h-9" />
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* bottom meta */}
      <div className="px-4 py-3 text-[12px] text-slate-500 border-t border-slate-800/70">
        Drives are ignored for <span className="font-medium text-slate-300">output</span> &amp; supply pins.
        For <span className="font-medium text-slate-300">PULSE</span>, blank fields fall back to the current
        model (TR/TF/PW/PER) and VDD configured above.
      </div>
    </div>
  );
}
