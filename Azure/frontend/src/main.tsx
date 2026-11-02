import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, beginOAuth, Subscription } from "./api";
import "./styles.css";

function App() {
  const [connection, setConnection] = useState("loading");
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [identity, setIdentity] = useState("");
  const [manualToken, setManualToken] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [devMode] = useState(import.meta.env.DEV);

  const discover = async () => {
    setBusy(true); setMessage("");
    try { const data = await api.discover(); setSubscriptions(data.subscriptions); setConnection("connected"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Subscription discovery failed"); }
    finally { setBusy(false); }
  };
  const load = async () => { try { const data = await api.connection(); setConnection(data.status); if (data.connected) await discover(); } catch (error) { setConnection("unavailable"); setMessage(error instanceof Error ? error.message : "Backend unavailable"); } };
  const saveSelection = async () => { try { await api.select(subscriptions.filter((item) => item.selected).map((item) => item.id)); setMessage("Subscription selection saved."); } catch (error) { setMessage(error instanceof Error ? error.message : "Selection failed"); } };
  const configureIdentity = async () => { try { await api.devSession(identity); setMessage("Local identity configured."); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Identity setup failed"); } };
  const submitManualToken = async () => { try { await api.manualToken(manualToken); setManualToken(""); setMessage("Temporary token submitted to the local backend memory store."); await discover(); } catch (error) { setMessage(error instanceof Error ? error.message : "Temporary token rejected"); } };
  useEffect(() => { void load(); }, []);

  return <main className="shell">
    <header className="topbar"><span className="logo">U</span><span className="brand">Unified Cloud Platform</span><span className="environment">Azure integration</span></header>
    <section className="hero"><p className="eyebrow">Microsoft Azure</p><h1>Cloud visibility with consent.</h1><p className="intro">Connect through Microsoft Entra or use the explicitly enabled local developer token path. All Azure API calls remain backend-mediated.</p></section>
    {devMode && <section className="panel developer"><p className="eyebrow">Local development</p><h2>Choose a test identity</h2><p className="muted">This creates an HttpOnly local development cookie. It is never accepted outside development mode.</p><div className="form-row"><input aria-label="Local test identity" value={identity} onChange={(event) => setIdentity(event.target.value)} placeholder="developer-a" /><button onClick={() => void configureIdentity()} disabled={!identity || busy}>Set identity</button></div><label className="token-label">Temporary ARM access token<input type="password" autoComplete="off" value={manualToken} onChange={(event) => setManualToken(event.target.value)} placeholder="Disabled unless ENABLE_MANUAL_AZURE_TOKEN_INPUT=true" /></label><div className="form-row"><button onClick={() => void submitManualToken()} disabled={!manualToken || busy}>Use temporary token</button><button className="secondary" onClick={() => { setManualToken(""); void api.clearManualToken().then(() => setMessage("Temporary token cleared.")); }}>Clear token</button></div></section>}
    <section className="panel"><div><p className="eyebrow">Connection</p><h2>{connection === "connected" ? "Azure is connected" : "Connect Microsoft Azure"}</h2><p className="muted">Status: <span className="status-text">{connection}</span></p></div>{connection === "connected" ? <button onClick={() => void discover()} disabled={busy}>Refresh discovery</button> : <button onClick={beginOAuth}>Connect Microsoft Azure</button>}</section>
    {message && <p className="notice" role="status">{message}</p>}
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">Access</p><h2>Subscriptions</h2></div><button className="secondary" onClick={() => void saveSelection()} disabled={!subscriptions.length || busy}>Save selection</button></div>{subscriptions.length === 0 ? <p className="muted">No authorized subscriptions have been returned.</p> : <div className="subscriptions">{subscriptions.map((item, index) => <label className="subscription" key={item.id}><input type="checkbox" checked={Boolean(item.selected)} onChange={(event) => setSubscriptions((all) => all.map((x, i) => i === index ? { ...x, selected: event.target.checked } : x))} /><span><strong>{item.display_name}</strong><small>{item.id} · {item.state ?? "unknown state"}</small></span></label>)}</div>}</section>
    <footer>Live Azure data is shown only from backend API responses. Tokens are not stored in browser storage.</footer>
  </main>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
