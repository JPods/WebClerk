/**
 * windowChannel — the one channel between WC3 windows (Bill, 2026-10-30).
 *
 * A message reaches every listener: this page's (its floating windows) at once, and every
 * other WC3 tab or browser window through BroadcastChannel, which skips its own sender.
 * The API layer announces every save and delete, so a panel hears a record saved anywhere.
 *
 * Usage:
 *   // DataBrowser sends when selection changes:
 *   windowChannel.send({ type: 'record-selected', model: 'serial', id: 42 })
 *
 *   // JSON Viewer listens and reloads:
 *   windowChannel.on('record-selected', (msg) => { if (msg.model === myModel) reload(msg.id) })
 *
 * Message types:
 *   record-selected  — user clicked a record in DataBrowser
 *   record-saved     — a record was saved (any window; sent by wcapiSave)
 *   record-deleted   — a record was deleted (sent by deleteRecord)
 *   model-changed    — DataBrowser switched models
 *   theme-changed    — theme toggled (sync across windows)
 */

export type ChannelMessage = {
  type: 'record-selected' | 'record-saved' | 'record-deleted' | 'model-changed' | 'theme-changed';
  model?: string;
  id?: number;
  field?: string;
  data?: unknown;
  source?: string;    // window identifier so sender can ignore own messages
};

type MessageHandler = (msg: ChannelMessage) => void;

const CHANNEL_NAME = 'wc3-databrowser';
const handlers: Map<string, Set<MessageHandler>> = new Map();

let channel: BroadcastChannel | null = null;
// Unique ID for this window — prevents self-echo
const windowId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

function deliver(msg: ChannelMessage): void {
  handlers.get(msg.type)?.forEach((fn) => fn(msg));
  handlers.get('*')?.forEach((fn) => fn(msg));
}

function getChannel(): BroadcastChannel {
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL_NAME);
    channel.onmessage = (event: MessageEvent<ChannelMessage>) => {
      if (event.data?.type) deliver(event.data);
    };
  }
  return channel;
}

/** Send to this page's listeners and to every other WC3 window. */
function send(msg: ChannelMessage): void {
  const out = { ...msg, source: windowId };
  deliver(out);
  getChannel().postMessage(out);
}

/** Listen for a specific message type (or '*' for all) */
function on(type: string, handler: MessageHandler): () => void {
  getChannel(); // ensure channel is open
  if (!handlers.has(type)) handlers.set(type, new Set());
  handlers.get(type)!.add(handler);
  // Return cleanup function
  return () => { handlers.get(type)?.delete(handler); };
}

/** Remove a specific handler */
function off(type: string, handler: MessageHandler): void {
  handlers.get(type)?.delete(handler);
}

/** Close the channel (cleanup on unmount) */
function close(): void {
  channel?.close();
  channel = null;
  handlers.clear();
}

export const windowChannel = { send, on, off, close, windowId };
export default windowChannel;
