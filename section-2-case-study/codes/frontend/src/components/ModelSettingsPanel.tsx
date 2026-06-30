import React, { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Search, Save, Settings, Wifi, X } from "lucide-react";
import {
  getModelSettings,
  getModels,
  ModelProvider,
  ModelSettings,
  saveModelSettings,
  testModelConnection
} from "../api/client";

const DEFAULT_SETTINGS: ModelSettings = {
  provider: "lm-studio",
  base_url: "http://localhost:1234/v1",
  model: "",
  timeout_seconds: 300
};

type Props = {
  open: boolean;
  onClose: () => void;
};

export function ModelSettingsPanel({ open, onClose }: Props) {
  const [settings, setSettings] = useState<ModelSettings>(DEFAULT_SETTINGS);
  const [models, setModels] = useState<string[]>([]);
  const [status, setStatus] = useState("Loading model settings");
  const [isBusy, setIsBusy] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    getModelSettings()
      .then((loaded) => {
        setSettings({
          ...loaded,
          provider: loaded.provider === "mock" ? "lm-studio" : loaded.provider
        });
        setStatus("Model settings loaded");
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : String(error)));
  }, []);

  const update = (patch: Partial<ModelSettings>) => {
    setIsSaved(false);
    setSettings((current) => ({ ...current, ...patch }));
  };

  const fetchModels = async () => {
    setIsBusy(true);
    setStatus("Fetching models");
    try {
      const nextModels = await getModels(settings);
      setModels(nextModels);
      if (!settings.model && nextModels[0]) update({ model: nextModels[0] });
      setStatus(nextModels.length ? "Models loaded" : "Connected, but no models were returned");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsBusy(false);
    }
  };

  const testConnection = async () => {
    setIsBusy(true);
    setStatus("Testing connection");
    try {
      const result = await testModelConnection(settings);
      const nextModels = result.models ?? [];
      setModels(nextModels);
      if (!settings.model && nextModels[0]) update({ model: nextModels[0] });
      if (!result.text_json_ok) {
        setStatus(result.text_json_issue?.reason || result.text_json_issue?.message || "Connection works, but text JSON preflight failed");
      } else {
        setStatus(result.model_available ? "Connection ready" : "Connection works, choose an available model");
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsBusy(false);
    }
  };

  const save = async () => {
    setIsBusy(true);
    setStatus("Saving settings");
    try {
      const saved = await saveModelSettings(settings);
      setSettings(saved);
      setIsSaved(true);
      setStatus("Settings saved for the next upload");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsBusy(false);
    }
  };

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="settings-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-settings-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="panel-title">
          <div className="panel-heading">
            <Settings size={18} />
            <h2 id="model-settings-title">LLM Settings</h2>
          </div>
          <button className="icon-button close-button" type="button" onClick={onClose} title="Close" aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <label className="field">
          <span>Provider</span>
          <select
            value={settings.provider}
            onChange={(event) => update({ provider: event.target.value as ModelProvider })}
          >
            <option value="lm-studio">LM Studio</option>
            <option value="openai-compatible">OpenAI compatible</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>

        <label className="field">
          <span>URL</span>
          <input
            value={settings.base_url}
            onChange={(event) => update({ base_url: event.target.value })}
            placeholder="http://localhost:1234/v1"
          />
        </label>

        <label className="field">
          <span>Model</span>
          <input
            list="available-models"
            value={settings.model}
            onChange={(event) => update({ model: event.target.value })}
            placeholder="Choose or type a model"
          />
          <datalist id="available-models">
            {models.map((model) => (
              <option key={model} value={model} />
            ))}
          </datalist>
        </label>

        <label className="field">
          <span>Timeout seconds</span>
          <input
            type="number"
            min="1"
            step="1"
            value={settings.timeout_seconds}
            onChange={(event) => update({ timeout_seconds: Math.max(1, Number(event.target.value) || 1) })}
          />
        </label>

        <div className="settings-actions">
          <button type="button" className="secondary-action search-action" onClick={fetchModels} disabled={isBusy}>
            {isBusy ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            Search Models
          </button>
          <button type="button" className="secondary-action" onClick={testConnection} disabled={isBusy}>
            <Wifi size={16} />
            Test
          </button>
          <button type="button" className="save-action" onClick={save} disabled={isBusy}>
            {isSaved ? <CheckCircle2 size={16} /> : <Save size={16} />}
            Save
          </button>
        </div>

        {models.length ? (
          <div className="model-results">
            <span>Available Models</span>
            <div className="model-list">
              {models.map((model) => (
                <button
                  type="button"
                  key={model}
                  className={model === settings.model ? "model-option selected" : "model-option"}
                  onClick={() => update({ model })}
                >
                  {model}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className={isSaved ? "settings-status success" : "settings-status"}>{status}</div>
      </aside>
    </div>
  );
}
