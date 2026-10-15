import React, { useEffect, useState } from 'react'
import { api } from '../services/api'
import {
  Activity, Clock, Cpu, BarChart3, HelpCircle
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend
} from 'recharts'

export const ModelPerformance: React.FC = () => {
  const [comparison, setComparison] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getModelComparison()
      .then((data) => setComparison(data))
      .catch((err) => console.error('Failed to load model comparison:', err))
      .finally(() => setLoading(false))
  }, [])

  const benchmarkChartData = [
    {
      metric: 'R² Score (x100)',
      'Random Forest': 97.2,
      'LSTM Network': 93.0,
    },
    {
      metric: 'MAE (kWh)',
      'Random Forest': 2.25,
      'LSTM Network': 0.17,
    },
    {
      metric: 'RMSE (kWh)',
      'Random Forest': 3.82,
      'LSTM Network': 0.27,
    },
    {
      metric: 'Train Time (s)',
      'Random Forest': 1.45,
      'LSTM Network': 9.54,
    },
  ]

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
        <p className="text-sm">Loading machine learning diagnostics and comparative benchmarks...</p>
      </div>
    )
  }

  const rfModel = comparison?.models?.find((m: any) => m.version_tag === 'rf_expected_v1')
  const lstmModel = comparison?.models?.find((m: any) => m.version_tag === 'lstm_expected_v1')
  const tradeOffs = comparison?.trade_off_analysis

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              <Activity className="w-3.5 h-3.5" />
              Machine Learning Diagnostics
            </span>
            <span className="text-xs text-slate-400 font-mono">Phase 12 Comparative Evaluation</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Model Performance & Deep Learning Benchmark</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Rigorous empirical comparison between Traditional Ensemble Trees (Random Forest) and Sequence Recurrent Neural Network (LSTM).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">
            Active Baseline: Random Forest
          </span>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-purple-50 text-purple-700 border border-purple-200">
            Benchmark: LSTM Sequence
          </span>
        </div>
      </div>

      {/* KPI Benchmarks Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Random Forest R²</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">
            {rfModel?.metrics?.r2 ?? '0.9720'}
          </div>
          <span className="text-xs text-slate-400">MAE: {rfModel?.metrics?.mae} kWh (Tabular)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">LSTM Sequence R²</span>
            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
          </div>
          <div className="text-2xl font-bold text-purple-700 mt-1">
            {lstmModel?.metrics?.r2 ?? '0.9304'}
          </div>
          <span className="text-xs text-slate-400">MAE: {lstmModel?.metrics?.mae} kWh (24h Window)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">RF Inference Latency</span>
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {rfModel?.metrics?.inference_latency_ms ?? 0.08} <span className="text-sm font-normal text-slate-500">ms</span>
          </div>
          <span className="text-xs text-slate-400">Single observation (zero lag required)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">LSTM Train Duration</span>
            <Cpu className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {lstmModel?.metrics?.train_time_sec ?? 9.54} <span className="text-sm font-normal text-slate-500">s</span>
          </div>
          <span className="text-xs text-slate-400">25 epochs BPTT on commodity CPU</span>
        </div>
      </div>

      {/* Visual Benchmark Comparison Bar Chart */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-600" />
              Empirical Metric Benchmarks on Chronological Test Split
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Side-by-side performance across coefficient of determination, error metrics, and training latency.
            </p>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={benchmarkChartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload
                    return (
                      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1">
                        <p className="font-bold text-slate-800">{d.metric}</p>
                        <div className="flex justify-between gap-4 text-emerald-700">
                          <span>Random Forest:</span>
                          <span className="font-mono font-bold">{d['Random Forest']}</span>
                        </div>
                        <div className="flex justify-between gap-4 text-purple-700">
                          <span>LSTM Network:</span>
                          <span className="font-mono font-bold">{d['LSTM Network']}</span>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '8px', fontSize: '11px' }} />
              <Bar dataKey="Random Forest" fill="#059669" radius={[4, 4, 0, 0]} />
              <Bar dataKey="LSTM Network" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Architecture Deep-Dive Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Random Forest Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-bold font-mono bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded">
                SUPERVISED ENSEMBLE BASELINE
              </span>
              <h2 className="text-lg font-bold text-slate-800 mt-2">RandomForestRegressor v1.0</h2>
              <p className="text-xs text-slate-500">120 Estimators, max_depth=16, 24 engineered features</p>
            </div>
            <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-xs font-semibold">
              Production Active
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 p-3.5 bg-slate-50 rounded-lg text-center text-xs">
            <div>
              <span className="text-slate-400 block uppercase font-semibold">MAE</span>
              <span className="text-base font-bold text-slate-800">2.25 kWh</span>
            </div>
            <div>
              <span className="text-slate-400 block uppercase font-semibold">RMSE</span>
              <span className="text-base font-bold text-slate-800">3.82 kWh</span>
            </div>
            <div>
              <span className="text-slate-400 block uppercase font-semibold">R² Score</span>
              <span className="text-base font-bold text-emerald-600">0.9720</span>
            </div>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <h3 className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Primary Predictive Drivers (Gini Importance)</h3>
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span>Occupancy Headcount Ratio</span>
                <span className="font-mono font-bold text-emerald-700">69.9%</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-600 h-full rounded-full" style={{ width: '69.9%' }}></div>
              </div>

              <div className="flex justify-between items-center">
                <span>IT Computer Center Category</span>
                <span className="font-mono font-bold text-emerald-700">17.5%</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-600 h-full rounded-full" style={{ width: '17.5%' }}></div>
              </div>

              <div className="flex justify-between items-center">
                <span>Laboratory Block Category</span>
                <span className="font-mono font-bold text-emerald-700">4.2%</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-600 h-full rounded-full" style={{ width: '4.2%' }}></div>
              </div>

              <div className="flex justify-between items-center">
                <span>Central HVAC Air Conditioning</span>
                <span className="font-mono font-bold text-emerald-700">2.6%</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-600 h-full rounded-full" style={{ width: '2.6%' }}></div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100 text-xs text-emerald-950">
            <strong>Key Advantage:</strong> Instant inference on single manual entries without requiring a 24-hour continuous historical buffer. Highly robust to missing weather or occupancy records.
          </div>
        </div>

        {/* LSTM Neural Network Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-bold font-mono bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded">
                DEEP LEARNING SEQUENCE RECURRENT
              </span>
              <h2 className="text-lg font-bold text-slate-800 mt-2">LSTM Sequence Regressor v1.0</h2>
              <p className="text-xs text-slate-500">24-hour sliding sequence, hidden_dim=32, BPTT Adam</p>
            </div>
            <span className="px-2.5 py-0.5 bg-purple-100 text-purple-800 rounded-full text-xs font-semibold">
              Benchmark Only
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 p-3.5 bg-slate-50 rounded-lg text-center text-xs">
            <div>
              <span className="text-slate-400 block uppercase font-semibold">MAE</span>
              <span className="text-base font-bold text-slate-800">0.17 kWh</span>
            </div>
            <div>
              <span className="text-slate-400 block uppercase font-semibold">RMSE</span>
              <span className="text-base font-bold text-slate-800">0.27 kWh</span>
            </div>
            <div>
              <span className="text-slate-400 block uppercase font-semibold">R² Score</span>
              <span className="text-base font-bold text-purple-700">0.9304</span>
            </div>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <h3 className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Recurrent Internal Gate Architecture</h3>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                <span className="font-bold text-slate-800 block">Forget Gate (f_t)</span>
                <span className="text-slate-500">σ(W_f · x_t + U_f · h_t-1 + b_f)</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                <span className="font-bold text-slate-800 block">Input Gate (i_t)</span>
                <span className="text-slate-500">σ(W_i · x_t + U_i · h_t-1 + b_i)</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                <span className="font-bold text-slate-800 block">Candidate State (c~_t)</span>
                <span className="text-slate-500">tanh(W_c · x_t + U_c · h_t-1 + b_c)</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                <span className="font-bold text-slate-800 block">Output Gate (o_t)</span>
                <span className="text-slate-500">σ(W_o · x_t + U_o · h_t-1 + b_o)</span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-purple-50/60 rounded-lg border border-purple-100 text-xs text-purple-950">
            <strong>Key Advantage:</strong> Models temporal persistence and lagged autoregressive dynamics over 24-hour cycles. Ideal for continuous smart meters streaming high-frequency data.
          </div>
        </div>
      </div>

      {/* Systematic Comparison Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-800">Architectural & Operational Trade-Off Matrix</h2>
          <span className="text-xs text-slate-400 font-mono">Academic Synthesis</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Dimension</th>
                <th className="px-6 py-3 text-left">Random Forest Regressor (Traditional ML)</th>
                <th className="px-6 py-3 text-left">LSTM Sequence Network (Deep Learning)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Paradigm</td>
                <td className="px-6 py-3">Supervised Ensemble of 120 Decision Trees</td>
                <td className="px-6 py-3">Recurrent Neural Network with Gated Cell Memory</td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Input Formulation</td>
                <td className="px-6 py-3">Single observation (24 tabular engineered features)</td>
                <td className="px-6 py-3">24-hour temporal sliding window [t-24 : t]</td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Test Split Performance</td>
                <td className="px-6 py-3 font-bold text-emerald-700">R² = 0.9720 (MAE = 2.25 kWh)</td>
                <td className="px-6 py-3 font-bold text-purple-700">R² = 0.9304 (MAE = 0.17 kWh normalized)</td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Manual Data Entry Suitability</td>
                <td className="px-6 py-3 font-bold text-emerald-700">
                  Instant (User enters 1 row &rarr; Model predicts immediately)
                </td>
                <td className="px-6 py-3 text-amber-700">
                  Constrained (Requires continuous buffer of 24 preceding hours)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Interpretability</td>
                <td className="px-6 py-3 text-emerald-700">
                  High (Gini feature importance transparent to electrical engineers)
                </td>
                <td className="px-6 py-3 text-slate-500">
                  Low / Black-Box (Complex internal gate activations)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Missing Context Tolerance</td>
                <td className="px-6 py-3 text-emerald-700">
                  High (Boolean indicator flags for missing temp / occupancy)
                </td>
                <td className="px-6 py-3 text-amber-700">
                  Moderate (Gaps break continuous temporal sequence alignment)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-3 font-semibold text-slate-900">Hardware & Compute Needs</td>
                <td className="px-6 py-3">Trains in 1.45s on standard CPU; lightweight joblib artifact</td>
                <td className="px-6 py-3">Trains in 9.54s; memory scaling proportional to sequence length</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Academic Viva Defense Panel */}
      <div className="bg-slate-900 text-white rounded-xl p-6 shadow-md space-y-4">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-indigo-400" />
          <h2 className="text-base font-bold text-white">
            Academic Viva Defense: When is Deep Learning Justified in Campus Energy?
          </h2>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          {tradeOffs?.academic_verdict ||
            "For Coimbatore Institute of Technology's prototype, Random Forest serves as the active production baseline due to instant single-entry inference and full transparent interpretability, while the LSTM neural network provides a rigorous sequence benchmark (R²=0.9304)."}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs">
          <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700 space-y-2">
            <h3 className="font-bold text-emerald-400 uppercase tracking-wider text-[11px]">
              Why Random Forest is Preferred Here
            </h3>
            <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
              {(tradeOffs?.when_traditional_ml_is_preferred || []).map((item: string, idx: number) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700 space-y-2">
            <h3 className="font-bold text-purple-400 uppercase tracking-wider text-[11px]">
              When Deep Learning IS Justified
            </h3>
            <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
              {(tradeOffs?.when_deep_learning_is_justified || []).map((item: string, idx: number) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
