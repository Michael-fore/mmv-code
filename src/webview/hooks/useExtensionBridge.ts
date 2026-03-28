import { useCallback, useEffect, useRef } from "react";
import type { WebviewToHost, HostToWebview } from "../../shared/types.js";

// Declare the VS Code API type
interface VsCodeApi {
  postMessage(msg: WebviewToHost): void;
  getState(): unknown;
  setState(state: unknown): void;
}

declare function acquireVsCodeApi(): VsCodeApi;

// acquireVsCodeApi() can only be called ONCE — store the result
let vscodeApi: VsCodeApi | null = null;

function getVsCodeApi(): VsCodeApi | null {
  if (vscodeApi) return vscodeApi;
  try {
    vscodeApi = acquireVsCodeApi();
    return vscodeApi;
  } catch {
    // Not running in VS Code webview (e.g., dev mode)
    return null;
  }
}

type MessageHandler = (msg: HostToWebview) => void;

export function useExtensionBridge() {
  const handlersRef = useRef<Set<MessageHandler>>(new Set());

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      const msg = event.data as HostToWebview;
      for (const handler of handlersRef.current) {
        handler(msg);
      }
    };

    window.addEventListener("message", listener);
    return () => window.removeEventListener("message", listener);
  }, []);

  const send = useCallback((msg: WebviewToHost) => {
    const api = getVsCodeApi();
    if (api) {
      api.postMessage(msg);
    } else {
      console.log("[bridge] postMessage (no VS Code API):", msg);
    }
  }, []);

  const subscribe = useCallback((handler: MessageHandler) => {
    handlersRef.current.add(handler);
    return () => {
      handlersRef.current.delete(handler);
    };
  }, []);

  return { send, subscribe };
}
