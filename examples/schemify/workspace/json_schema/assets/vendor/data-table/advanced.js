import { $ as e, A as t, B as n, C as r, Ct as i, D as a, E as o, F as s, G as c, H as l, J as u, K as d, L as f, M as ee, N as te, O as ne, P as re, R as ie, S as p, St as m, T as h, Tt as g, U as _, V as v, W as y, Y as b, Z as x, _ as S, a as C, at as w, b as T, bt as E, c as D, d as O, dt as k, et as A, f as j, ft as M, g as N, gt as P, h as F, ht as I, i as L, it as R, j as z, k as B, l as V, m as H, n as U, nt as W, o as G, ot as K, p as q, q as J, r as ae, rt as oe, s as se, st as ce, tt as le, u as ue, v as de, vt as Y, w as fe, x as pe, y as me, z as he } from "./VisualizationRegistry-D2a_eV3R.js";
import { a as ge, i as _e, n as ve, o as X, r as ye, t as be } from "./CodeMirrorExpressionEditor-BOO5Hr5e.js";
import { t as xe } from "./SQLFilterModal-BeUNtaTR.js";
import { t as Se } from "./FilterPresetPanel-D93JC2sc.js";
import { t as Z } from "./DerivedColumnEditPanel-DYb9GbYR.js";
import { t as Ce } from "./DerivedColumnModal-DOUycpeX.js";
//#region src/derived/DefaultExpressionEditor.ts
var we = class {
	element;
	textarea;
	errorDiv;
	contextDiv;
	prefix;
	messages;
	constructor(e, t, n = "dt", r = x) {
		this.prefix = n, this.messages = r, this.element = document.createElement("div"), this.textarea = document.createElement("textarea"), this.textarea.className = `${this.prefix}-expr-editor-input`, this.textarea.rows = 4, this.textarea.placeholder = this.messages.derived.expressionPlaceholder, this.textarea.spellcheck = !1, this.textarea.autocomplete = "off", this.element.appendChild(this.textarea), this.errorDiv = document.createElement("div"), this.errorDiv.className = `${this.prefix}-expr-editor-error`, this.errorDiv.style.display = "none", this.element.appendChild(this.errorDiv), this.contextDiv = document.createElement("div"), this.contextDiv.className = `${this.prefix}-expr-editor-context`, this.buildContextText(t), this.element.appendChild(this.contextDiv), e.appendChild(this.element);
	}
	getValue() {
		return this.textarea.value;
	}
	setValue(e) {
		this.textarea.value = e;
	}
	focus() {
		this.textarea.focus();
	}
	setError(e) {
		e === null ? (this.textarea.classList.remove(`${this.prefix}-expr-editor-input--error`), this.errorDiv.textContent = "", this.errorDiv.style.display = "none") : (this.textarea.classList.add(`${this.prefix}-expr-editor-input--error`), this.errorDiv.textContent = e, this.errorDiv.style.display = "");
	}
	updateCompletionContext(e) {
		this.buildContextText(e);
	}
	destroy() {
		this.element.parentNode && this.element.parentNode.removeChild(this.element);
	}
	buildContextText(e) {
		if (e.columns.length === 0) {
			this.contextDiv.textContent = "";
			return;
		}
		let t = e.columns.map((e) => `${e.name} (${e.type})`).join(", ");
		this.contextDiv.textContent = `${this.messages.derived.availableColumnsLabel} ${t}`;
	}
}, Te = X.map((e) => e.name);
//#endregion
//#region src/statistics/ColumnStatsTypes.ts
function Ee(e) {
	switch (e) {
		case "integer":
		case "float":
		case "decimal": return "numeric";
		case "string":
		case "boolean":
		case "uuid": return "categorical";
		case "date":
		case "timestamp": return "temporal";
		case "time": return "time";
		case "interval": return "interval";
		default: throw new g(`Unknown DataType: ${e}`, { code: "INVARIANT" });
	}
}
//#endregion
//#region src/statistics/StatsComputer.ts
async function De(e, t, n, i, a) {
	let o = P(n), s = o ? `WHERE ${o}` : "", c = Y(t), l = Y(e);
	try {
		let e;
		try {
			let t = `
        SELECT
          COUNT(*) as total,
          COUNT(${c}) as non_null,
          COUNT(*) - COUNT(${c}) as null_count,
          MIN(${c})::VARCHAR as min_val,
          MAX(${c})::VARCHAR as max_val,
          APPROX_QUANTILE(${c}, 0.5)::VARCHAR as median_val
        FROM ${l}
        ${s}
      `;
			e = await i.query(t);
		} catch {
			let t = `
        SELECT
          COUNT(*) as total,
          COUNT(${c}) as non_null,
          COUNT(*) - COUNT(${c}) as null_count,
          MIN(${c})::VARCHAR as min_val,
          MAX(${c})::VARCHAR as max_val,
          NULL as median_val
        FROM ${l}
        ${s}
      `;
			e = await i.query(t);
		}
		if (e.length === 0) return {
			kind: "interval",
			totalRows: a ?? 0,
			nonNullCount: 0,
			nullCount: 0,
			filteredTotalRows: a === void 0 ? null : 0,
			minDisplay: null,
			maxDisplay: null,
			medianDisplay: null
		};
		let t = e[0], n = Number(t.total), o = Number(t.non_null), u = Number(t.null_count);
		return {
			kind: "interval",
			totalRows: a ?? n,
			nonNullCount: o,
			nullCount: u,
			filteredTotalRows: a === void 0 ? null : n,
			minDisplay: t.min_val ? r(p(t.min_val)) : null,
			maxDisplay: t.max_val ? r(p(t.max_val)) : null,
			medianDisplay: t.median_val ? r(p(t.median_val)) : null
		};
	} catch (e) {
		return console.error(`[StatsComputer] Failed to fetch interval stats for column "${t}":`, e instanceof Error ? e.message : String(e)), {
			kind: "interval",
			totalRows: a ?? 0,
			nonNullCount: 0,
			nullCount: 0,
			filteredTotalRows: a === void 0 ? null : 0,
			minDisplay: null,
			maxDisplay: null,
			medianDisplay: null
		};
	}
}
//#endregion
//#region src/visualizations/BaseStatsPanel.ts
var Oe = class {
	container;
	column;
	options;
	destroyed = !1;
	constructor(e, t, n) {
		this.container = e, this.column = t, this.options = n;
	}
	setHoverStats(e) {}
	async updateFilters(e) {
		this.destroyed || (this.options = {
			...this.options,
			filters: e
		});
	}
	destroy() {
		this.destroyed = !0;
	}
	isDestroyed() {
		return this.destroyed;
	}
	getColumn() {
		return this.column;
	}
}, Q = !1;
function $() {
	Q || (Q = !0, console.warn("VisualizationFactory is deprecated; use `VisualizationRegistry` and pass `visualizationRegistry` to `createDataTable()`. The static wrapper will be removed in a future minor release."));
}
var ke = class {
	static register(e) {
		$(), U.register(e);
	}
	static unregister(e) {
		return $(), U.unregister(e);
	}
	static create(e, t, n) {
		return $(), U.create(e, t, n);
	}
	static isApplicable(e) {
		return $(), U.isApplicable(e);
	}
	static getRegisteredTypes() {
		return $(), U.getRegisteredTypes();
	}
	static resetToDefaults() {
		$(), U.resetToDefaults();
	}
};
//#endregion
export { te as AddColumnButton, s as AnnotationPopover, E as AnnotationStore, n as AutoSave, Oe as BaseStatsPanel, N as BaseVisualization, pe as CellRenderer, be as CodeMirrorExpressionEditor, ne as ColumnHeader, re as ColumnHeaderTooltipPopover, o as ColumnReorder, S as CrossfilterCoordinator, Te as DUCKDB_FUNCTIONS, X as DUCKDB_FUNCTION_DETAILS, F as DateHistogram, we as DefaultExpressionEditor, Z as DerivedColumnEditPanel, I as DerivedColumnManager, Ce as DerivedColumnModal, e as EventEmitter, v as ExportDialog, z as FilterBar, ee as FilterChip, B as FilterPanel, t as FilterPanelField, Se as FilterPresetPanel, h as HiddenColumnsGutter, H as Histogram, O as InteractionManager, q as IntervalHistogram, fe as KeyboardNavigator, k as SNAPSHOT_VERSION, xe as SQLFilterModal, A as StateActions, ue as StatsPanelCoordinator, me as TableBody, de as TableContainer, j as TimeHistogram, le as UndoManager, V as ValueCounts, T as VirtualScroller, ke as VisualizationFactory, W as applySnapshot, ve as buildCompletionContext, oe as captureSnapshot, a as clampUnpinnedIndex, d as copyRowsToClipboard, J as copyToClipboard, ye as createSqlExtensions, w as createTableState, _e as dataTableHighlighting, ge as dataTableTheme, R as derivedColumnsEqual, u as exportFromState, y as exportJSONFromState, l as exportParquetFromState, b as exportToCSV, c as exportToJSON, _ as exportToParquet, De as fetchIntervalStats, f as formatCount, ie as formatDefaultStats, he as formatStatValue, m as generateAnnotationId, K as initializeColumnsFromSchema, i as isAnnotationIdShape, ae as isCategoricalType, L as isDateType, C as isIntervalType, G as isNumericType, M as isPooledVectorRef, se as isTimeType, D as needsVisualization, ce as resetTableState, Ee as statsKindForDataType };

//# sourceMappingURL=advanced.js.map