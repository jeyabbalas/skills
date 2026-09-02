import { $ as e, At as t, B as n, Dt as r, Et as i, F as a, Ft as o, I as s, It as c, Mt as l, Nt as u, Ot as d, P as f, Pt as p, Q as m, R as ee, Tt as h, V as g, Z as _, _ as v, _t as y, at as te, bt as ne, ct as re, d as ie, et as ae, f as b, gt as x, h as S, jt as C, kt as w, l as T, lt as E, m as D, mt as O, n as oe, p as k, pt as A, st as se, t as j, tt as ce, u as le, ut as M, v as ue, vt as N, wt as P, xt as F, yt as I } from "./VisualizationRegistry-D2a_eV3R.js";
//#region src/core/checkBrowserSupport.ts
function de() {
	let e = [];
	return typeof Worker > "u" && e.push("Worker"), typeof WebAssembly > "u" && e.push("WebAssembly"), typeof indexedDB > "u" && e.push("IndexedDB"), typeof ResizeObserver > "u" && e.push("ResizeObserver"), typeof BigInt > "u" && e.push("BigInt"), typeof structuredClone > "u" && e.push("structuredClone"), {
		supported: e.length === 0,
		missing: e
	};
}
//#endregion
//#region src/core/stylesheet.ts
function fe(e) {
	let t = e ?? document.documentElement;
	return getComputedStyle(t).getPropertyValue("--dt-stylesheet-loaded").trim() !== "";
}
//#endregion
//#region src/data/WorkerBridge.ts
var L = 3e4, pe = class {
	worker = null;
	pendingRequests = /* @__PURE__ */ new Map();
	messageId = 0;
	initPromise = null;
	queryCache;
	initializeTimeoutMs;
	workerFactory;
	workerUrl;
	duckdbBundles;
	constructor(e) {
		this.queryCache = new I(e?.cache), this.initializeTimeoutMs = e?.initializeTimeoutMs ?? L, this.workerFactory = e?.workerFactory, this.workerUrl = e?.workerUrl, this.duckdbBundles = e?.duckdbBundles;
	}
	createWorker() {
		if (this.workerFactory) try {
			let e = this.workerFactory();
			if (!e || typeof e.postMessage != "function") throw Error("workerFactory returned a non-Worker value");
			return e;
		} catch (e) {
			throw new p(`Custom workerFactory failed: ${e instanceof Error ? e.message : String(e)}`, {
				code: "WORKER_CRASHED",
				cause: e,
				details: { source: "workerFactory" }
			});
		}
		if (this.workerUrl !== void 0) try {
			return new Worker(this.workerUrl, { type: "module" });
		} catch (e) {
			throw new p(`Failed to construct worker from workerUrl: ${e instanceof Error ? e.message : String(e)}`, {
				code: "WORKER_CRASHED",
				cause: e,
				details: {
					source: "workerUrl",
					workerUrl: String(this.workerUrl)
				}
			});
		}
		return new Worker(new URL(
			/* @vite-ignore */
			"" + new URL("assets/worker-SarKVnD7.js", import.meta.url).href,
			"" + import.meta.url
		), { type: "module" });
	}
	async initialize() {
		return this.initPromise ||= new Promise((e, t) => {
			let n = !1, r = (e) => {
				n || (n = !0, clearTimeout(i), e());
			}, i = setTimeout(() => {
				r(() => {
					this.worker &&= (this.worker.terminate(), null), this.initPromise = null, t(new p(`WorkerBridge.initialize() timed out after ${this.initializeTimeoutMs}ms (worker did not reach ready state or DuckDB failed to init). If your app bundles the worker separately, verify it can import @duckdb/duckdb-wasm.`, {
						code: "WORKER_INIT_TIMEOUT",
						details: { timeoutMs: this.initializeTimeoutMs }
					}));
				});
			}, this.initializeTimeoutMs);
			try {
				this.worker = this.createWorker(), this.worker.onmessage = this.handleMessage.bind(this), this.worker.onerror = (e) => {
					r(() => t(new p(`Worker error: ${e.message}`, {
						code: "WORKER_CRASHED",
						cause: e
					})));
				};
				let n = (i) => {
					if (i.data.id === "__ready__") {
						this.worker.removeEventListener("message", n);
						let i = this.duckdbBundles ? { bundles: this.duckdbBundles } : {};
						this.sendMessage("init", i).then(() => r(() => e())).catch((e) => r(() => t(e)));
					}
				};
				this.worker.addEventListener("message", n);
			} catch (e) {
				r(() => t(e));
			}
		}), this.initPromise;
	}
	async query(e, t, n) {
		this.ensureInitialized();
		let r = n?.cache !== !1 && this.isCacheable(e);
		if (r) {
			let t = this.queryCache.get(e);
			if (t !== void 0) return t;
		}
		let i = {
			sql: e,
			...n?.priority === void 0 ? {} : { priority: n.priority }
		}, a = (await this.sendMessage("query", i, void 0, t)).rows;
		return r && !t?.aborted && this.queryCache.set(e, a), a;
	}
	async loadData(e, t, n, r) {
		this.ensureInitialized();
		let i = {
			data: e,
			format: t.format,
			tableName: t.tableName
		}, a = await this.sendMessage("load", i, n, r);
		return {
			tableName: a.tableName,
			rowCount: a.rowCount,
			columns: a.columns,
			schema: a.schema
		};
	}
	async exportToBuffer(e, t, n) {
		this.ensureInitialized();
		let r = {
			sql: e,
			format: t
		}, i = await this.sendMessage("export", r, void 0, n);
		return new Uint8Array(i.buffer);
	}
	terminate() {
		if (!this.worker) return;
		this.worker.terminate(), this.worker = null, this.initPromise = null;
		let e = Array.from(this.pendingRequests.keys());
		for (let t of e) {
			let e = this.pendingRequests.get(t);
			e && (e.reject(new o("Worker terminated")), this.cleanupRequest(t));
		}
		this.queryCache.clear();
	}
	clearQueryCache() {
		this.queryCache.clear();
	}
	async dropTable(e) {
		this.ensureInitialized();
		let t = `"${e.replace(/"/g, "\"\"")}"`;
		await this.query(`DROP TABLE IF EXISTS ${t}`);
	}
	isInitialized() {
		return this.worker !== null && this.initPromise !== null;
	}
	ensureInitialized() {
		if (!this.worker) throw new h("WorkerBridge not initialized. Call initialize() first.", { code: "BRIDGE_NOT_READY" });
	}
	isCacheable(e) {
		return e.trimStart().toUpperCase().startsWith("SELECT");
	}
	generateId() {
		return `msg-${++this.messageId}`;
	}
	sendMessage(e, t, n, r) {
		return new Promise((i, a) => {
			let o = this.generateId(), s = null;
			if (r) {
				if (r.aborted) {
					a(new l("Operation aborted", { code: "QUERY_ABORTED" }));
					return;
				}
				s = () => {
					this.cleanupRequest(o);
					let e = {
						id: this.generateId(),
						type: "cancel",
						payload: { targetId: o }
					};
					this.worker?.postMessage(e), a(new l("Operation aborted", { code: "QUERY_ABORTED" }));
				}, r.addEventListener("abort", s);
			}
			this.pendingRequests.set(o, {
				resolve: i,
				reject: a,
				onProgress: n,
				signal: r,
				abortHandler: s
			});
			let c = {
				id: o,
				type: e,
				payload: t
			};
			this.worker.postMessage(c);
		});
	}
	cleanupRequest(e) {
		let t = this.pendingRequests.get(e);
		t?.signal && t.abortHandler && t.signal.removeEventListener("abort", t.abortHandler), this.pendingRequests.delete(e);
	}
	handleMessage(e) {
		let t = e.data;
		if (typeof t != "object" || !t) {
			console.warn("[WorkerBridge] dropping non-object worker message");
			return;
		}
		let n = t.id, r = t.type, i = t.payload;
		if (typeof n != "string") {
			console.warn("[WorkerBridge] dropping worker message with non-string id");
			return;
		}
		if (n === "__ready__") return;
		let a = this.pendingRequests.get(n);
		if (a) switch (r) {
			case "result":
				this.cleanupRequest(n), a.resolve(i);
				break;
			case "error":
				if (this.cleanupRequest(n), typeof i != "object" || !i) {
					a.reject(new p("Worker error response missing payload", {
						code: "WORKER_PROTOCOL_VIOLATION",
						details: {
							id: n,
							type: r
						}
					}));
					break;
				}
				a.reject(c(i));
				break;
			case "progress":
				a.onProgress && typeof i == "object" && i && a.onProgress(i);
				break;
			default: console.warn(`[WorkerBridge] dropping worker message with unknown type: ${String(r)}`), this.cleanupRequest(n), a.reject(new p(`Worker sent unknown message type: ${String(r)}`, {
				code: "WORKER_PROTOCOL_VIOLATION",
				details: {
					id: n,
					type: String(r)
				}
			}));
		}
	}
}, R = /* @__PURE__ */ new Set([
	"contains",
	"starts",
	"ends",
	"regex"
]), z = /* @__PURE__ */ new Set([
	"range",
	"point",
	"set",
	"not-set",
	"null",
	"not-null",
	"pattern",
	"raw-sql"
]), me = class {
	presets;
	constructor() {
		this.presets = A([]);
	}
	save(e, t, n, r) {
		let i = e.trim();
		if (!i) throw new h("Preset name is required", { code: "OPTIONS_INVALID" });
		if (this.presets.get().some((e) => e.name === i)) throw new h(`A preset named "${i}" already exists`, {
			code: "PRESET_DUPLICATE_NAME",
			details: { name: i }
		});
		let a = Date.now(), o = {
			id: crypto.randomUUID(),
			name: i,
			description: r?.trim() || void 0,
			filters: t.map(M),
			sortColumns: n ? n.map((e) => ({ ...e })) : void 0,
			createdAt: a,
			updatedAt: a
		};
		return this.presets.set([...this.presets.get(), o]), o;
	}
	load(e, t) {
		let n = this.presets.get().find((t) => t.id === e);
		if (!n) return;
		let r = n.filters.map(E).filter((e) => e !== null);
		t.loadFilterPreset(r, n.sortColumns);
	}
	delete(e) {
		this.presets.set(this.presets.get().filter((t) => t.id !== e));
	}
	rename(e, t) {
		let n = t.trim();
		if (!n) return;
		let r = this.presets.get(), i = r.find((t) => t.id === e);
		if (!(!i || i.name === n)) {
			if (r.some((t) => t.id !== e && t.name === n)) throw new h(`A preset named "${n}" already exists`, {
				code: "PRESET_DUPLICATE_NAME",
				details: { name: n }
			});
			this.presets.set(r.map((t) => t.id === e ? {
				...t,
				name: n,
				updatedAt: Date.now()
			} : t));
		}
	}
	update(e, t) {
		this.presets.set(this.presets.get().map((n) => n.id === e ? {
			...n,
			filters: t.map(M),
			updatedAt: Date.now()
		} : n));
	}
	exportToJSON() {
		let e = {
			version: 1,
			presets: this.presets.get()
		};
		return JSON.stringify(e, null, 2);
	}
	importFromJSON(e) {
		let t = [], n;
		try {
			n = JSON.parse(e);
		} catch {
			return {
				imported: 0,
				errors: ["Invalid JSON"]
			};
		}
		if (typeof n != "object" || !n) return {
			imported: 0,
			errors: ["Expected a JSON object"]
		};
		let r = n;
		if (typeof r.version != "number") return {
			imported: 0,
			errors: ["Missing or invalid \"version\" field"]
		};
		if (!Array.isArray(r.presets)) return {
			imported: 0,
			errors: ["Missing or invalid \"presets\" array"]
		};
		let i = [], a = new Set(this.presets.get().map((e) => e.name)), o = r.presets;
		for (let e = 0; e < o.length; e++) {
			let n = o[e];
			if (typeof n != "object" || !n) {
				t.push(`Preset ${e}: not an object`);
				continue;
			}
			let r = n;
			if (typeof r.name != "string" || !r.name.trim()) {
				t.push(`Preset ${e}: missing or empty name`);
				continue;
			}
			let s = r.name.trim();
			if (a.has(s)) {
				t.push(`Preset ${e}: name "${s}" already exists; skipped`);
				continue;
			}
			if (!Array.isArray(r.filters)) {
				t.push(`Preset ${e}: missing filters array`);
				continue;
			}
			let c = [], l = 0;
			for (let e of r.filters) {
				if (typeof e != "object" || !e) {
					l++;
					continue;
				}
				let t = e;
				if (typeof t.type != "string" || !z.has(t.type)) {
					l++;
					continue;
				}
				if (typeof t.column != "string" || !t.column) {
					l++;
					continue;
				}
				let n = !1;
				switch (t.type) {
					case "raw-sql":
						(typeof t.sql != "string" || typeof t.id != "string") && (n = !0);
						break;
					case "range":
						(t.min === void 0 || t.max === void 0) && (n = !0);
						break;
					case "set":
					case "not-set":
						Array.isArray(t.values) || (n = !0);
						break;
					case "pattern": (typeof t.pattern != "string" || typeof t.mode != "string" || !R.has(t.mode)) && (n = !0);
				}
				if (n) {
					l++;
					continue;
				}
				c.push(e);
			}
			if (l > 0 && t.push(`Preset ${e}: skipped ${l} invalid filter(s)`), c.length === 0 && r.filters.length > 0) {
				t.push(`Preset ${e}: no valid filters`);
				continue;
			}
			a.add(s), i.push({
				id: crypto.randomUUID(),
				name: s,
				description: typeof r.description == "string" && r.description.trim() || void 0,
				filters: c,
				sortColumns: (() => {
					if (!Array.isArray(r.sortColumns)) return;
					let e = r.sortColumns.filter((e) => typeof e == "object" && !!e && typeof e.column == "string" && (e.direction === "asc" || e.direction === "desc"));
					return e.length > 0 ? e : void 0;
				})(),
				createdAt: typeof r.createdAt == "number" ? r.createdAt : Date.now(),
				updatedAt: typeof r.updatedAt == "number" ? r.updatedAt : Date.now()
			});
		}
		return i.length > 0 && this.presets.set([...this.presets.get(), ...i]), {
			imported: i.length,
			errors: t
		};
	}
	loadPresets(e) {
		this.presets.set(e.map((e) => ({ ...e })));
	}
	getPresets() {
		return this.presets.get();
	}
}, B = class {
	registry = [];
	register(e) {
		let t = this.registry.findIndex((t) => t.name === e.name);
		t >= 0 ? this.registry[t] = e : this.registry.push(e);
	}
	unregister(e) {
		let t = this.registry.findIndex((t) => t.name === e);
		return t >= 0 && (this.registry.splice(t, 1), !0);
	}
	create(e, t, n) {
		let r = [...this.registry].sort((e, t) => t.priority - e.priority);
		for (let i of r) if (i.isApplicable(t.type)) return new i.constructor(e, t, n);
		return null;
	}
	isApplicable(e) {
		return this.registry.some((t) => t.isApplicable(e.type));
	}
	getRegisteredTypes() {
		return this.registry.map((e) => e.name);
	}
	resetToDefaults() {
		this.registry = [];
	}
}, he = new B(), ge = !1, V = [
	"light",
	"dark",
	"auto"
];
function _e(e, t) {
	if (e === void 0) return "auto";
	if (typeof e == "string" && V.includes(e)) return e;
	throw new h(`${t}: invalid colorScheme. Expected 'light', 'dark', or 'auto'.`, {
		code: "OPTIONS_INVALID",
		details: { received: e }
	});
}
async function ve(e) {
	return e instanceof Blob && !(e instanceof File) ? e.arrayBuffer() : e;
}
async function H(r) {
	if (r.strictBrowserCheck) {
		let e = de();
		if (!e.supported) throw new p(`Browser is missing required APIs: ${e.missing.join(", ")}.`, {
			code: "WORKER_UNSUPPORTED",
			details: { missing: e.missing }
		});
	}
	let o = _e(r.colorScheme, "createDataTable"), c = m(_, r.messages), l = !r.bridge, u = r.bridge ?? new pe(r.bridgeOptions);
	await u.initialize();
	let y = te(), x = r.undoRedo === !1 ? void 0 : new ce(), C = new ae(y, u, x), w = new e((e, t) => {
		if (t === "error" || t === "warning") {
			console.error("[data-table] listener threw inside", String(t), "handler", e);
			return;
		}
		let n = e instanceof i ? e : new h(e instanceof Error ? e.message : String(e), {
			code: "OPTIONS_INVALID",
			cause: e
		});
		w.emit("error", {
			error: n,
			source: "listener"
		});
	}), E = null, O = !1, A = null;
	if (r.persistence !== !1) {
		let e = typeof r.persistence == "object" ? r.persistence : {};
		e.sessionStore ? E = e.sessionStore : (E = new re({ onLoadIssue: (e) => {
			R || w.emit("warning", {
				code: e.code,
				message: `Persisted session for "${e.tableName}" was rejected: version ${e.details.version} is outside the supported range [1, ${e.details.expectedMax}]. Booting fresh.`,
				details: {
					tableName: e.tableName,
					...e.details
				}
			});
		} }), O = !0);
		try {
			await E.open();
		} catch (e) {
			w.emit("warning", {
				code: "PERSISTENCE_UNAVAILABLE",
				message: "IndexedDB is unavailable; session persistence is disabled.",
				details: { reason: e instanceof Error ? e.message : String(e) }
			}), E = null, O = !1;
		}
	}
	let j = null, M = !1;
	if (r.presets !== !1) {
		let e = typeof r.presets == "object" ? r.presets : {};
		M = e.manager === void 0, j = e.manager ?? new me();
	}
	let N = new ne({ tableName: y.baseTableName }), P = new a({
		classPrefix: r.classPrefix ?? "dt",
		portalTarget: r.portalTarget
	}), F = new f({
		classPrefix: r.classPrefix ?? "dt",
		portalTarget: r.portalTarget
	}), I = new ue(r.container, y, C, u, {
		rowHeight: r.rowHeight,
		headerHeight: r.headerHeight,
		fetchBlockSize: r.fetchBlockSize,
		rowCacheRows: r.rowCacheRows,
		prefetch: r.prefetch,
		classPrefix: r.classPrefix ?? "dt",
		instanceId: r.instanceId,
		showExpressionFilter: r.expressionFilter !== !1,
		showAddColumnButton: r.derivedColumns !== !1,
		showDerivedColumnEditIcon: r.derivedColumns !== !1,
		editorFactory: r.editorFactory,
		presetManager: j ?? void 0,
		portalTarget: r.portalTarget,
		colorScheme: o,
		messages: c,
		annotations: N,
		annotationPopover: P,
		columnHeaderTooltipPopover: F
	}), L = I.getInstanceId();
	if (!ge && !fe()) {
		ge = !0;
		let e = c.errors.stylesheetMissing;
		w.listenerCount("warning") === 0 && console.warn(e), w.emit("warning", {
			code: "STYLESHEET_MISSING",
			message: e
		});
	}
	let R = !1, z = r.visualizations === !1 ? null : new ie(), B = new v(y, C, u, void 0, { onFilterCycleComplete: (e) => {
		R || w.emit("filterChange", {
			filters: [...e],
			filteredRowCount: y.filteredRows.get(),
			totalRowCount: y.totalRows.get()
		});
	} }), V = [], H = Promise.resolve(), U = /* @__PURE__ */ new Map(), W = /* @__PURE__ */ new Map(), G = r.visualizationRegistry ?? oe, K = null, q = /* @__PURE__ */ new Map(), ye = r.statsPanelRegistry ?? he, J = (e, t, n) => {
		let r = e instanceof i ? e : new h(e instanceof Error ? e.message : String(e), {
			code: "INVARIANT",
			cause: e,
			details: {
				column: t,
				phase: n
			}
		});
		w.emit("error", {
			error: r,
			source: "stats-panel"
		});
	};
	r.visualizations !== !1 && C.setOnFilterRemove((e) => {
		U.delete(e), W.delete(e), z?.clearColumn(e);
	});
	let be = () => {
		let e = r.visualizations !== !1, t = y.tableName.get();
		if (!t) return;
		for (let e of V) {
			let t = e.getColumn();
			if (e instanceof D || e instanceof S || e instanceof b || e instanceof k) {
				let n = e.getBrushState();
				n && U.set(t.name, n);
				let r = e.getSelectionState();
				(r.selectedBin !== null || r.selectedNull) && W.set(t.name, r);
			} else if (e instanceof T) {
				let n = e.getSelectionState();
				(n.selectedSegments.length > 0 || n.selectedNull) && W.set(t.name, {
					selectedSegments: n.selectedSegments,
					selectedNull: n.selectedNull
				});
			}
		}
		for (let e of V) B.unregister(e.getColumn().name);
		for (let e of V) e.destroy();
		V = [], z?.clear();
		for (let [e, t] of q) try {
			t.destroy();
		} catch (t) {
			J(t, e, "destroy");
		}
		if (q.clear(), K && K.destroy(), K = new le(y), !e) {
			H = Promise.resolve();
			return;
		}
		let n = [], i = I.getColumnHeaders();
		for (let e of i) {
			let i = e.getColumn(), a = e.getStatsElement(), o = null;
			if (ye.isApplicable(i)) {
				let e = {
					tableName: t,
					bridge: u,
					filters: y.filters.get(),
					messages: c,
					onError: (e, t) => {
						let n = e;
						n.details = {
							...n.details ?? {},
							column: t.column,
							phase: t.phase
						}, w.emit("error", {
							error: e,
							source: "stats-panel"
						});
					}
				};
				try {
					a.innerHTML = "", o = ye.create(a, i, e);
				} catch (e) {
					J(e, i.name, "construct"), o = null;
				}
				if (o) {
					q.set(i.name, o), K.register(i.name, o);
					try {
						o.update(null);
					} catch (e) {
						J(e, i.name, "update");
					}
				}
			}
			if (!G.isApplicable(i)) {
				if (!o) {
					let e = y.totalRows.get();
					a.innerHTML = `<span class="${r.classPrefix ?? "dt"}-stats-line1">${s(c.statistics.rowCount(e))}</span>`;
				}
				continue;
			}
			let l = e.getVizContainer(), d = null, f = !1, p = () => {
				let e = y.filteredRows.get(), t = y.totalRows.get();
				return y.filters.get().length > 0 ? `<span class="${r.classPrefix ?? "dt"}-stats-line1">${s(c.statistics.filteredRowCount(e, t))}</span>` : `<span class="${r.classPrefix ?? "dt"}-stats-line1">${s(c.statistics.rowCount(t))}</span>`;
			};
			o || (a.innerHTML = p());
			let m, h = {
				tableName: t,
				bridge: u,
				filters: y.filters.get(),
				onFilterChange: (e) => {
					B.handleFilterChange(i.name, e);
				},
				onDefaultStatsChange: (e) => {
					if (o) {
						try {
							o.update(e);
						} catch (e) {
							J(e, i.name, "update");
						}
						return;
					}
					let t = ee(e, i.type, c);
					d = t, f || (a.innerHTML = t);
				},
				onStatsChange: (e) => {
					if (o) {
						try {
							o.setHoverStats(e);
						} catch (e) {
							J(e, i.name, "hover");
						}
						return;
					}
					e ? (f = !0, a.innerHTML = e) : (f = !1, a.innerHTML = d ?? p());
				},
				onBrushCommit: (e) => {
					if (m && (z?.pushBrush(e, m), m instanceof D || m instanceof S || m instanceof b || m instanceof k)) {
						let t = m.getBrushState();
						t && U.set(e, t);
					}
				},
				onBrushClear: (e) => {
					z?.removeColumn(e), U.delete(e);
				},
				onSelectionChange: (e, t) => {
					if (m) if (t) if (z?.pushSelection(e, m), m instanceof T) {
						let t = m.getSelectionState();
						W.set(e, {
							selectedSegments: t.selectedSegments,
							selectedNull: t.selectedNull
						});
					} else (m instanceof D || m instanceof S || m instanceof b || m instanceof k) && W.set(e, m.getSelectionState());
					else z?.removeColumn(e), W.delete(e);
				},
				onError: (e) => {
					w.emit("error", {
						error: e,
						source: "visualization"
					});
				}
			}, g = G.create(l, i, h);
			if (!g) continue;
			m = g, V.push(m), B.register(i.name, m), n.push(m.waitForData());
			let _ = U.get(i.name), v = W.get(i.name);
			(_ || v) && m.waitForData().then(() => {
				m && (_ && (m instanceof D || m instanceof S || m instanceof b || m instanceof k) && (m.setBrushState(_), z?.pushBrush(i.name, m)), v && (m instanceof T && v.selectedSegments !== void 0 ? (m.setSelectionState({
					selectedSegments: v.selectedSegments,
					selectedNull: v.selectedNull
				}), (v.selectedSegments.length > 0 || v.selectedNull) && z?.pushSelection(i.name, m)) : (m instanceof D || m instanceof S || m instanceof b || m instanceof k) && v.selectedBin !== void 0 && (m.setSelectionState({
					selectedBin: v.selectedBin,
					selectedNull: v.selectedNull
				}), (v.selectedBin !== null || v.selectedNull) && z?.pushSelection(i.name, m))));
			});
		}
		n.push(B.syncExistingFilters()), n.push(K.syncExistingFilters(y.filters.get())), H = Promise.allSettled(n).then(() => void 0);
	};
	E && r.persistence !== !1 && (A = new n(y, E, {
		undoManager: x,
		presetManager: j ?? void 0,
		annotationStore: N,
		onError: (e) => {
			w.emit("error", {
				error: e,
				source: "persistence"
			});
		}
	}), A.enable());
	let Y = null, xe = () => {
		r.exportDialog !== !1 && (Y || (Y = new g(y, u, {
			classPrefix: r.classPrefix ?? "dt",
			instanceId: L,
			colorSchemeSource: I.getElement(),
			messages: c
		}), I.getPortalTarget().appendChild(Y.getElement())), Y.open());
	}, X = [], Z = null;
	X.push(y.sortColumns.subscribe((e) => {
		w.emit("sortChange", { sortColumns: [...e] });
	})), X.push(y.selectedRows.subscribe((e) => {
		w.emit("selectionChange", { selectedRows: new Set(e) });
	}));
	let Q = !1, Se = () => {
		Q && (Q = !1, !R && w.emit("columnChange", {
			visibleColumns: [...y.visibleColumns.get()],
			pinnedColumns: [...y.pinnedColumns.get()],
			columnOrder: [...y.columnOrder.get()]
		}));
	}, Ce = () => {
		Q || (Q = !0, queueMicrotask(Se));
	};
	X.push(y.visibleColumns.subscribe(Ce)), X.push(y.pinnedColumns.subscribe(Ce)), C.setOnDerivedChange((e) => {
		w.emit("derivedChange", e);
	}), x && (X.push(x.canUndoSignal.subscribe(() => {
		w.emit("undoChange", {
			canUndo: x.canUndo,
			canRedo: x.canRedo
		});
	})), X.push(x.canRedoSignal.subscribe(() => {
		w.emit("undoChange", {
			canUndo: x.canUndo,
			canRedo: x.canRedo
		});
	})));
	let we = !1, Te = () => {
		we || R || (we = !0, queueMicrotask(() => {
			we = !1, !R && y.schema.get().length !== 0 && y.tableName.get() && be();
		}));
	};
	X.push(y.schema.subscribe(Te)), X.push(y.visibleColumns.subscribe(Te)), X.push(y.tableName.subscribe(Te));
	let Ee = () => {
		if (R || !y.tableName.get()) return;
		let e = I.getColumnHeaders(), t = y.totalRows.get(), n = y.filteredRows.get(), i = y.filters.get(), a = r.classPrefix ?? "dt";
		for (let r of e) {
			let e = r.getColumn();
			if (G.isApplicable(e)) continue;
			let o = q.get(e.name);
			if (o) {
				if (!o.isDestroyed()) continue;
				q.delete(e.name);
			}
			let s = r.getStatsElement();
			s.innerHTML = i.length > 0 ? `<span class="${a}-stats-line1">${n.toLocaleString()} / ${t.toLocaleString()} rows</span>` : `<span class="${a}-stats-line1">${t.toLocaleString()} rows</span>`;
		}
	};
	X.push(y.filters.subscribe(Ee)), X.push(y.filteredRows.subscribe(Ee));
	async function De(e, n) {
		let r = typeof e == "string" ? e : e instanceof File ? e.name : "in-memory";
		w.emit("loadStart", { source: r }), A?.disable();
		try {
			let t = await ve(e);
			if (R) throw new d("DataTable is destroyed; load aborted.");
			let r = y.baseTableName.get() ?? y.tableName.get();
			M && j?.presets.set([]), N.clear("all"), u.clearQueryCache();
			let i = {
				...n ?? {},
				format: n?.sourceFormat ?? n?.format,
				sessionStore: n?.sessionStore ?? E ?? void 0,
				presetManager: n?.presetManager ?? j ?? void 0,
				annotationStore: N
			};
			if (await C.loadData(t, i), R || (await Promise.all([I.whenBodyReady(), H]), R)) throw new d("DataTable is destroyed; load aborted.");
			w.emit("loadComplete", {
				tableName: y.tableName.get() ?? "",
				rowCount: y.totalRows.get(),
				schema: [...y.schema.get()]
			});
			let a = y.baseTableName.get() ?? y.tableName.get();
			if (r && r !== a && typeof u.dropTable == "function") try {
				await u.dropTable(r);
			} catch (e) {
				console.warn(`[data-table] Failed to drop previous table "${r}":`, e);
			}
		} catch (e) {
			let n = e instanceof i ? e : new t(e instanceof Error ? e.message : String(e), {
				code: "PARSE_FAILED",
				cause: e
			});
			throw R || (w.emit("loadError", { error: n }), w.emit("error", {
				error: n,
				source: "load"
			})), n;
		} finally {
			R || A?.enable();
		}
	}
	Z = { bridgeReady: !0 }, w.emit("ready", Z), r.source !== void 0 && await De(r.source, {
		tableName: r.tableName,
		sourceFormat: r.sourceFormat
	});
	async function Oe() {
		if (!R) {
			R = !0, C.markDestroyed(), w.emit("destroy", {}), A?.disable(), N.destroy(), P.destroy(), F.destroy();
			for (let e of X) try {
				e();
			} catch {}
			X.length = 0;
			for (let e of V) e.destroy();
			V = [], z?.destroy(), B.destroy();
			for (let [e, t] of q) try {
				t.destroy();
			} catch (t) {
				J(t, e, "destroy");
			}
			if (q.clear(), K?.destroy(), K = null, Y?.destroy(), Y = null, I.destroy(), O && E) try {
				E.close();
			} catch {}
			if (!l && typeof u.dropTable == "function") {
				let e = y.baseTableName.get() ?? y.tableName.get();
				if (e) try {
					await u.dropTable(e);
				} catch (t) {
					console.warn(`[data-table] Failed to drop base table "${e}" on destroy:`, t);
				}
			}
			l && u.terminate(), w.removeAllListeners();
		}
	}
	async function ke() {
		A?.disable();
		try {
			if (E) {
				let e = y.baseTableName.get() ?? y.tableName.get();
				e && await E.delete(e);
			}
			if (R) throw new d("DataTable is destroyed; clearSession aborted.");
			se(y), x?.clear(), M && j?.presets.set([]), N.clear("all"), u.clearQueryCache();
		} finally {
			R || A?.enable();
		}
	}
	let $ = (e) => {
		if (R) throw new d(`DataTable is destroyed; cannot call ${e}().`);
	};
	return {
		state: y,
		actions: C,
		bridge: u,
		container: I,
		annotations: N,
		instanceId: L,
		loadData: (e, t) => R ? Promise.reject(new d("DataTable is destroyed; cannot call loadData().")) : De(e, t),
		on(e, t) {
			if ($("on"), e === "ready" && Z) {
				let e = Z;
				queueMicrotask(() => {
					R || t(e);
				});
			}
			return w.on(e, t), () => w.off(e, t);
		},
		off(e, t) {
			$("off"), w.off(e, t);
		},
		openExportDialog() {
			$("openExportDialog"), xe();
		},
		clearSession() {
			return R ? Promise.reject(new d("DataTable is destroyed; cannot call clearSession().")) : ke();
		},
		destroy: Oe,
		isDestroyed: () => R,
		isPersistenceActive: () => E !== null,
		setColorScheme(e) {
			$("setColorScheme");
			let t = _e(e, "setColorScheme");
			o = t, I.setColorScheme(t);
		},
		getColorScheme: () => o
	};
}
//#endregion
//#region src/index.ts
var U = "0.7.0";
//#endregion
export { F as ANNOTATION_FILE_VERSION, P as AnnotationError, h as ConfigurationError, i as DataTableError, r as DerivedColumnError, d as DestroyedError, w as ExportError, me as FilterPresetManager, t as LoadError, C as PersistenceError, l as QueryError, O as ROWID_COLUMN, u as SQLValidationError, re as SessionStore, B as StatsPanelRegistry, U as VERSION, j as VisualizationRegistry, pe as WorkerBridge, p as WorkerInitError, o as WorkerTerminatedError, de as checkBrowserSupport, H as createDataTable, he as defaultStatsPanelRegistry, _ as defaultStrings, oe as defaultVisualizationRegistry, E as deserializeFilter, x as filtersToWhereClause, y as formatSQLValue, fe as isStylesheetLoaded, m as mergeStrings, N as quoteIdentifier, M as serializeFilter };

//# sourceMappingURL=data-table.js.map