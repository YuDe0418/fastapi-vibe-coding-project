import * as Alert from '@radix-ui/react-alert-dialog';
import { Button } from './button';
import { useState } from 'react';
import { toast } from 'sonner';
export function Confirm({ title, description, onConfirm, children }: { title: string; description: string; onConfirm: () => Promise<void>; children: React.ReactNode }) {
 const [open, setOpen] = useState(false); const [busy, setBusy] = useState(false);
 return <Alert.Root open={open} onOpenChange={v => !busy && setOpen(v)}><Alert.Trigger asChild>{children}</Alert.Trigger><Alert.Portal><Alert.Overlay className="dialog-overlay"/><Alert.Content className="dialog"><Alert.Title className="text-xl font-semibold">{title}</Alert.Title><Alert.Description className="muted my-4">{description}</Alert.Description><div className="flex justify-end gap-2"><Alert.Cancel asChild><Button variant="outline" disabled={busy}>取消</Button></Alert.Cancel><Button variant="destructive" disabled={busy} onClick={async () => { setBusy(true); try { await onConfirm(); setOpen(false); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); } }}>{busy ? '處理中…' : '確認刪除'}</Button></div></Alert.Content></Alert.Portal></Alert.Root>;
}
