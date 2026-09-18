/**
 * windowChannel — cross-window messaging for DataBrowser ecosystem.
 *
 * Uses BroadcastChannel API (built-in, no dependencies).
 * Any window on the same origin can send/receive messages.
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
 *   record-saved     — a record was saved (any window)
 *   record-deleted   — a record was deleted
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

function getChannel(): BroadcastChannel {
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL_NAME);
    channel.onmessage = (event: MessageEvent<ChannelMessage>) => {
      const msg = event.data;
      if (!msg?.type) return;
      // Don't process messages from this same window
      if (msg.source === windowId) return;
      // Fire type-specific handlers
      const typeHandlers = handlers.get(msg.type);
      if (typeHandlers) typeHandlers.forEach((fn) => fn(msg));
      // Fire wildcard handlers
      const allHandlers = handlers.get('*');
      if (allHandlers) allHandlers.forEach((fn) => fn(msg));
    };
  }
  return channel;
}

/** Send a message to all other windows */
function send(msg: ChannelMessage): void {
  getChannel().postMessage({ ...msg, source: windowId });
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
