import { t as e } from "./rolldown-runtime-Dy4uBu1J.js";
import { X as t, Z as n } from "./VisualizationRegistry-D2a_eV3R.js";
//#region src/filters/FilterPresetPanel.ts
var r = /* @__PURE__ */ e({ FilterPresetPanel: () => i }), i = class {
	presetManager;
	state;
	actions;
	element;
	nameInput;
	descriptionInput;
	saveBtn;
	presetListEl;
	exportBtn;
	importStatusEl;
	fileInput;
	prefix;
	colorSchemeSource;
	messages;
	isOpen = !1;
	destroyed = !1;
	modalHost = new t();
	unsubPresets = null;
	unsubFilters = null;
	constructor(e, t, r, i) {
		this.presetManager = e, this.state = t, this.actions = r, this.prefix = i?.classPrefix ?? "dt", this.colorSchemeSource = i?.colorSchemeSource, this.messages = i?.messages ?? n, this.element = this.createElement(), this.unsubPresets = this.presetManager.presets.subscribe(() => {
			this.destroyed || (this.renderPresetList(), this.updateExportButtonState());
		}), this.unsubFilters = this.state.filters.subscribe(() => {
			this.destroyed || this.updateSaveButtonState();
		});
	}
	createElement() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-filter-preset-panel`, t.style.display = "none", t.setAttribute("role", "dialog");
		let n = document.createElement("div");
		n.className = `${e}-filter-preset-header`;
		let r = document.createElement("span");
		r.className = `${e}-filter-preset-title`, r.textContent = this.messages.presets.title;
		let i = document.createElement("button");
		i.className = `${e}-filter-preset-close`, i.type = "button", i.setAttribute("aria-label", this.messages.presets.closeLabel), i.innerHTML = "\n      <svg viewBox=\"0 0 16 16\" width=\"14\" height=\"14\" fill=\"currentColor\" aria-hidden=\"true\">\n        <path d=\"M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z\"/>\n      </svg>\n    ", i.addEventListener("click", () => this.close()), n.appendChild(r), n.appendChild(i), t.appendChild(n);
		let a = document.createElement("div");
		a.className = `${e}-filter-preset-body`;
		let o = document.createElement("div");
		o.className = `${e}-filter-preset-save-section`, this.nameInput = document.createElement("input"), this.nameInput.type = "text", this.nameInput.className = `${e}-filter-input`, this.nameInput.placeholder = this.messages.presets.namePlaceholder, this.nameInput.addEventListener("input", () => this.updateSaveButtonState()), this.nameInput.addEventListener("keydown", (e) => {
			e.key === "Enter" && !this.saveBtn.disabled && this.handleSave();
		}), this.descriptionInput = document.createElement("textarea"), this.descriptionInput.className = `${e}-filter-input`, this.descriptionInput.placeholder = this.messages.presets.descriptionPlaceholder, this.descriptionInput.rows = 2, this.saveBtn = document.createElement("button"), this.saveBtn.className = `${e}-filter-preset-save-btn`, this.saveBtn.type = "button", this.saveBtn.textContent = this.messages.presets.saveButton, this.saveBtn.disabled = !0, this.saveBtn.addEventListener("click", () => this.handleSave()), o.appendChild(this.nameInput), o.appendChild(this.descriptionInput), o.appendChild(this.saveBtn), a.appendChild(o), a.appendChild(this.createDivider()), this.presetListEl = document.createElement("div"), this.presetListEl.className = `${e}-filter-preset-list`, a.appendChild(this.presetListEl), a.appendChild(this.createDivider());
		let s = document.createElement("div");
		s.className = `${e}-filter-preset-io`, this.exportBtn = document.createElement("button"), this.exportBtn.className = `${e}-filter-preset-io-btn`, this.exportBtn.type = "button", this.exportBtn.textContent = this.messages.presets.exportButton, this.exportBtn.disabled = this.presetManager.getPresets().length === 0, this.exportBtn.addEventListener("click", () => this.handleExport());
		let c = document.createElement("button");
		return c.className = `${e}-filter-preset-io-btn`, c.type = "button", c.textContent = this.messages.presets.importButton, c.addEventListener("click", () => this.fileInput.click()), this.fileInput = document.createElement("input"), this.fileInput.type = "file", this.fileInput.accept = ".json", this.fileInput.style.display = "none", this.fileInput.addEventListener("change", () => this.handleImport()), this.importStatusEl = document.createElement("span"), this.importStatusEl.className = `${e}-filter-preset-import-status`, s.appendChild(this.exportBtn), s.appendChild(c), s.appendChild(this.fileInput), s.appendChild(this.importStatusEl), a.appendChild(s), t.appendChild(a), t;
	}
	createDivider() {
		let e = document.createElement("div");
		return e.className = `${this.prefix}-filter-preset-divider`, e;
	}
	position(e) {
		let t = this.element.parentElement;
		if (!t) return;
		let n = t.getBoundingClientRect(), r = e.getBoundingClientRect(), i = r.left - n.left, a = r.bottom - n.top + 4, o = this.element.offsetWidth || 320;
		i + o > n.width && (i = Math.max(0, n.width - o)), this.element.style.left = `${i}px`, this.element.style.top = `${a}px`;
	}
	toggle(e) {
		this.isOpen ? this.close() : this.open(e);
	}
	open(e) {
		this.destroyed || (this.isOpen = !0, this.element.style.display = "", this.updateSaveButtonState(), this.updateExportButtonState(), this.renderPresetList(), this.position(e), this.modalHost.open({
			mode: "panel",
			element: this.element,
			initialFocus: this.nameInput,
			outsideClickIgnore: [`.${this.prefix}-filter-presets-btn`],
			onClose: () => this.handleHostClose(),
			colorSchemeSource: this.colorSchemeSource
		}));
	}
	close() {
		this.isOpen && this.modalHost.close();
	}
	handleHostClose() {
		this.isOpen = !1, this.element.style.display = "none", this.clearImportStatus();
	}
	handleSave() {
		let e = this.nameInput.value.trim();
		if (!e) {
			this.nameInput.classList.add(`${this.prefix}-filter-input--error`), setTimeout(() => {
				this.nameInput.classList.remove(`${this.prefix}-filter-input--error`);
			}, 1500);
			return;
		}
		let t = this.state.filters.get();
		if (t.length === 0) return;
		let n = this.descriptionInput.value.trim() || void 0, r = this.state.sortColumns.get();
		this.presetManager.save(e, t, r.length > 0 ? r : void 0, n), this.nameInput.value = "", this.descriptionInput.value = "", this.updateSaveButtonState();
	}
	handleLoad(e) {
		this.presetManager.load(e, this.actions), this.close();
	}
	handleDelete(e) {
		this.presetManager.delete(e);
	}
	handleExport() {
		let e = this.presetManager.exportToJSON(), t = new Blob([e], { type: "application/json" }), n = URL.createObjectURL(t), r = document.createElement("a");
		r.href = n, r.download = "filter-presets.json", r.click(), URL.revokeObjectURL(n);
	}
	handleImport() {
		let e = this.fileInput.files?.[0];
		if (!e) return;
		let t = new FileReader();
		t.onload = () => {
			let e = this.presetManager.importFromJSON(t.result);
			e.errors.length > 0 ? this.showImportStatus(this.messages.presets.importPartial(e.imported, e.errors.length), "warning") : e.imported > 0 ? this.showImportStatus(this.messages.presets.importSuccess(e.imported), "success") : this.showImportStatus(this.messages.presets.importEmpty, "warning"), this.fileInput.value = "";
		}, t.onerror = () => {
			this.showImportStatus(this.messages.presets.importFailed, "warning"), this.fileInput.value = "";
		}, t.readAsText(e);
	}
	showImportStatus(e, t) {
		this.importStatusEl.textContent = e, this.importStatusEl.className = `${this.prefix}-filter-preset-import-status ${this.prefix}-filter-preset-import-status--${t}`, setTimeout(() => this.clearImportStatus(), 4e3);
	}
	clearImportStatus() {
		this.importStatusEl.textContent = "", this.importStatusEl.className = `${this.prefix}-filter-preset-import-status`;
	}
	renderPresetList() {
		let e = this.prefix, t = this.presetManager.getPresets();
		if (this.presetListEl.innerHTML = "", t.length === 0) {
			let t = document.createElement("div");
			t.className = `${e}-filter-preset-empty`, t.textContent = this.messages.presets.emptyState, this.presetListEl.appendChild(t);
			return;
		}
		for (let e of t) this.presetListEl.appendChild(this.createPresetItem(e));
	}
	createPresetItem(e) {
		let t = this.prefix, n = document.createElement("div");
		n.className = `${t}-filter-preset-item`;
		let r = document.createElement("div");
		r.className = `${t}-filter-preset-item-header`;
		let i = document.createElement("div");
		i.className = `${t}-filter-preset-item-name`, i.textContent = e.name;
		let a = document.createElement("div");
		a.className = `${t}-filter-preset-item-meta`;
		let o = e.filters.length, s = new Date(e.updatedAt).toLocaleDateString("en-US", {
			month: "short",
			day: "numeric",
			year: "numeric"
		});
		if (a.textContent = this.messages.presets.meta(o, s), r.appendChild(i), r.appendChild(a), n.appendChild(r), e.description) {
			let r = document.createElement("div");
			r.className = `${t}-filter-preset-item-desc`, r.textContent = e.description, n.appendChild(r);
		}
		let c = document.createElement("div");
		c.className = `${t}-filter-preset-item-actions`;
		let l = document.createElement("button");
		l.className = `${t}-filter-preset-action-btn ${t}-filter-preset-action-btn--load`, l.type = "button", l.textContent = this.messages.presets.loadButton, l.addEventListener("click", () => this.handleLoad(e.id));
		let u = document.createElement("button");
		u.className = `${t}-filter-preset-action-btn ${t}-filter-preset-action-btn--delete`, u.type = "button", u.textContent = this.messages.presets.deleteButton;
		let d = document.createElement("div");
		d.className = `${t}-filter-preset-delete-confirm`, d.style.display = "none";
		let f = document.createElement("span");
		f.textContent = this.messages.presets.deleteConfirmText;
		let p = document.createElement("button");
		p.className = `${t}-filter-preset-action-btn ${t}-filter-preset-action-btn--delete`, p.type = "button", p.textContent = this.messages.common.yes, p.addEventListener("click", () => this.handleDelete(e.id));
		let m = document.createElement("button");
		return m.className = `${t}-filter-preset-action-btn`, m.type = "button", m.textContent = this.messages.common.no, m.addEventListener("click", () => {
			d.style.display = "none", u.style.display = "";
		}), d.appendChild(f), d.appendChild(p), d.appendChild(m), u.addEventListener("click", () => {
			u.style.display = "none", d.style.display = "flex";
		}), c.appendChild(l), c.appendChild(u), c.appendChild(d), n.appendChild(c), n;
	}
	updateSaveButtonState() {
		let e = this.state.filters.get().length > 0, t = this.nameInput.value.trim().length > 0;
		this.saveBtn.disabled = !e || !t;
	}
	updateExportButtonState() {
		this.exportBtn.disabled = this.presetManager.getPresets().length === 0;
	}
	getElement() {
		return this.element;
	}
	getIsOpen() {
		return this.isOpen;
	}
	destroy() {
		this.destroyed || (this.destroyed = !0, this.close(), this.modalHost.destroy(), this.unsubPresets &&= (this.unsubPresets(), null), this.unsubFilters &&= (this.unsubFilters(), null), this.element.parentNode && this.element.parentNode.removeChild(this.element));
	}
};
//#endregion
export { r as n, i as t };

//# sourceMappingURL=FilterPresetPanel-D93JC2sc.js.map