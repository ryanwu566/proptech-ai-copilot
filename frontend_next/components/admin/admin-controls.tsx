"use client";

import { useEffect, useRef, useState } from 'react';
import { useExperienceLocale } from '@/components/experience-locale-provider';
import { requestAdmin } from '@/lib/admin/client';
import { userParser, label } from '@/lib/admin/model';
import { adminCopy, type AdminCopyKey } from '@/lib/admin/copy';
import { AdminReadError } from '@/lib/admin/transport';
import styles from './admin-view.module.css';

type Account = ReturnType<typeof userParser>;
type AccountAction = 'suspend' | 'reactivate' | 'promote' | 'demote';
type Policy = { principal_class: 'authenticated' | 'anonymous'; request_hour: number; operation_hour: number; operation_day: number };
type Pending = { path: string; body: Record<string, string | number>; action: string; target: string };

function useOperator() {
  const { locale, copyFrom } = useExperienceLocale();
  const t = (key: AdminCopyKey) => copyFrom(adminCopy, key);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => { const value = new AbortController(); controller.current = value; return () => value.abort(); }, []);
  return { locale, t, request: (path: string, body?: object) => requestAdmin(path, body, controller.current?.signal) };
}

function CommandReview({ pending, onClose, onSaved }: { pending: Pending; onClose: () => void; onSaved: () => void }) {
  const { t, request } = useOperator();
  const [status, setStatus] = useState<'review' | 'saving' | 'uncertain' | 'denied' | 'conflict' | 'invalid_command' | 'not_found'>('review');
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  async function submit() {
    if (status === 'saving') return;
    setStatus('saving');
    try { await request(pending.path, pending.body); onSaved(); }
    catch (error) {
      if (error instanceof AdminReadError && error.code === 'cancelled') return;
      setStatus(error instanceof AdminReadError && ['denied','authentication'].includes(error.code) ? 'denied' : error instanceof AdminReadError && ['conflict','invalid_command','not_found'].includes(error.code) ? error.code as 'conflict' | 'invalid_command' | 'not_found' : 'uncertain');
    }
  }
  return <section className={styles.controls} aria-labelledby="command-review-title" aria-busy={status === 'saving'}>
    <h3 id="command-review-title" tabIndex={-1} ref={heading}>{t('review')}</h3>
    <p><strong>{pending.action}</strong></p>
    <p>{t('target')}: {pending.target}</p>
    <p>{t('reason')}: {pending.body.reason}</p>
    {['request_hour','operation_hour','operation_day'].filter((key) => pending.body[key] !== undefined).map((key) => <p key={key}>{t(key as AdminCopyKey)}: {pending.body[key]}</p>)}
    <p>{t('command_id')}: <code>{pending.body.command_id}</code></p>
    {status !== 'review' && status !== 'saving' && <p role="alert">{t(status === 'uncertain' ? 'uncertain' : status)}</p>}
    <div className={styles.actions}>
      {!['denied','conflict','invalid_command','not_found'].includes(status) && <button type="button" disabled={status === 'saving'} onClick={() => void submit()}>{t(status === 'saving' ? 'pending' : status === 'uncertain' ? 'retry' : 'confirm')}</button>}
      <button type="button" disabled={status === 'saving'} onClick={onClose}>{t('cancel')}</button>
    </div>
  </section>;
}

export function AccountControls({ onChanged }: { onChanged: () => void }) {
  const { locale, t, request } = useOperator();
  const [query, setQuery] = useState('');
  const [account, setAccount] = useState<Account | null>(null);
  const [reason, setReason] = useState('');
  const [action, setAction] = useState<AccountAction>('suspend');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState<Pending | null>(null);
  async function lookup() {
    if (busy) return;
    setBusy(true); setAccount(null); setError('');
    try { setAccount(userParser(await request(`/accounts/${query.trim().toLowerCase()}`))); }
    catch (error) { if (!(error instanceof AdminReadError && error.code === 'cancelled')) setError(error instanceof AdminReadError ? error.code : 'error'); }
    finally { setBusy(false); }
  }
  function review() {
    if (!account || !reason.trim()) return;
    const field = ['suspend','reactivate'].includes(action) ? 'status' : 'platform_role';
    const value = { suspend: 'suspended', reactivate: 'active', promote: 'platform_admin', demote: 'consumer' }[action]!;
    setPending({ path: `/accounts/${account.user_id}/commands`, target: account.user_id, body: { field, value, reason, command_id: crypto.randomUUID() }, action: t(action as AdminCopyKey) });
  }
  return <section className={styles.controls} aria-label={t('lookup')}>
    <h3>{t('lookup')}</h3><p>{t('safety')}</p>
    {!pending && <><form onSubmit={(event) => { event.preventDefault(); void lookup(); }} className={styles.form}>
      <label>{t('lookup_id')}<input disabled={busy} required pattern="[a-fA-F0-9-]{36}" maxLength={36} value={query} onChange={(e) => { setQuery(e.target.value); setAccount(null); }} autoComplete="off" /></label>
      <button disabled={busy} type="submit">{t(busy ? 'loading' : 'inspect')}</button>
    </form>
    {error && <p role="alert">{label(error, locale)}</p>}
    {account && <form onSubmit={(event) => { event.preventDefault(); review(); }} className={styles.form}>
      <p><code>{account.user_id}</code> · {label(account.status, locale)} · {label(account.platform_role, locale)}</p>
      <label>{t('actions')}<select value={action} onChange={(e) => setAction(e.target.value as AccountAction)}>{(['suspend','reactivate','promote','demote'] as const).map((value) => <option key={value} value={value}>{t(value)}</option>)}</select></label>
      <label>{t('reason')}<textarea required maxLength={500} value={reason} onChange={(e) => setReason(e.target.value.replace(/[\r\n\t]+/g, ' '))} /></label>
      <button type="submit" disabled={!reason.trim()}>{t('review')}</button>
    </form>}</>}
    {pending && <CommandReview pending={pending} onClose={() => setPending(null)} onSaved={() => { setPending(null); setAccount(null); onChanged(); }} />}
  </section>;
}

export function QuotaControls({ onChanged }: { onChanged: () => void }) {
  const { locale, t, request } = useOperator();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selected, setSelected] = useState('authenticated');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState<Pending | null>(null);
  const policy = policies.find((row) => row.principal_class === selected);
  async function load() {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const rows = await request('/quota-policy');
      if (!Array.isArray(rows) || rows.length !== 2 || rows.some((r) => !r || !['authenticated','anonymous'].includes(r.principal_class) || ['request_hour','operation_hour','operation_day'].some((k) => !Number.isSafeInteger(r[k]) || r[k] < 1 || r[k] > (k === 'operation_day' ? 1000000 : 100000)))) throw new Error('contract');
      setPolicies(rows);
    } catch (error) { if (!(error instanceof AdminReadError && error.code === 'cancelled')) setError(error instanceof AdminReadError ? error.code : 'error'); }
    finally { setBusy(false); }
  }
  return <section className={styles.controls} aria-label={t('quota_policy')}>
    <h3>{t('quota_policy')}</h3><p>{t('policy_scope')}</p>
    {!pending && <><button disabled={busy} onClick={() => void load()}>{t('manage_policy')}</button>
      {error && <p role="alert">{label(error, locale)}</p>}
      {policy && <form className={styles.form} onSubmit={(event) => { event.preventDefault(); if (reason.trim()) setPending({ path: '/quota-policy/commands', target: policy.principal_class, body: { ...policy, reason, command_id: crypto.randomUUID() }, action: t('quota_policy') }); }}>
        <label>{t('principal_class')}<select value={selected} onChange={(event) => setSelected(event.target.value)}>{policies.map((row) => <option key={row.principal_class} value={row.principal_class}>{label(row.principal_class, locale)}</option>)}</select></label>
        {(['request_hour','operation_hour','operation_day'] as const).map((key) => <label key={key}>{t(key)}<input type="number" required min={1} max={key === 'operation_day' ? 1000000 : 100000} value={policy[key] || ''} onChange={(event) => setPolicies((rows) => rows.map((row) => row.principal_class === selected ? { ...row, [key]: Number(event.target.value) } : row))} /></label>)}
        <label>{t('reason')}<textarea required maxLength={500} value={reason} onChange={(event) => setReason(event.target.value.replace(/[\r\n\t]+/g, ' '))} /></label>
        <button disabled={!reason.trim()} type="submit">{t('review')}</button>
      </form>}
    </>}
    {pending && <CommandReview pending={pending} onClose={() => setPending(null)} onSaved={() => { setPending(null); setPolicies([]); onChanged(); }} />}
  </section>;
}
