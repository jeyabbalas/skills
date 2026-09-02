import { t as e } from "./rolldown-runtime-Dy4uBu1J.js";
import { X as t, Z as n } from "./VisualizationRegistry-D2a_eV3R.js";
import { t as r } from "./CodeMirrorExpressionEditor-BOO5Hr5e.js";
import { t as i } from "./wireLiveCompletionContext-1rQH1ZoK.js";
//#region src/filters/SQLFilterModal.ts
var a = /* @__PURE__ */ e({ SQLFilterModal: () => o }), o = class {
	state;
	actions;
	element;
	dialogEl;
	titleEl;
	labelInput;
	editorContainer;
	validateBtn;
	previewEl;
	applyBtn;
	removeSection;
	removeBtn;
	removeConfirmDiv;
	prefix;
	instanceId;
	messages;
	editorFactory;
	colorSchemeSource;
	currentEditor = null;
	editorInputHandler = null;
	unsubLiveCompletion = null;
	isOpen = !1;
	destroyed = !1;
	validated = !1;
	applying = !1;
	validationVersion = 0;
	modalHost = new t();
	validationAbortController = null;
	currentFilterId = null;
	constructor(e, t, r) {
		this.state = e, this.actions = t, this.prefix = r?.classPrefix ?? "dt", this.instanceId = r?.instanceId ?? "", this.messages = r?.messages ?? n, this.editorFactory = r?.editorFactory, this.colorSchemeSource = r?.colorSchemeSource, this.element = this.createElement();
	}
	createElement() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-sql-filter-modal-backdrop`;
		let n = document.createElement("div");
		return n.className = `${e}-sql-filter-modal-dialog`, t.appendChild(n), n.appendChild(this.createHeader()), n.appendChild(this.createBody()), n.appendChild(this.createFooter()), this.dialogEl = n, t;
	}
	createHeader() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-sql-filter-modal-header`, this.titleEl = document.createElement("span"), this.titleEl.className = `${e}-sql-filter-modal-title`, this.titleEl.id = `${e}-${this.instanceId}-sql-filter-modal-title`, this.titleEl.textContent = this.messages.filters.sqlFilter.createTitle;
		let n = document.createElement("button");
		return n.className = `${e}-sql-filter-modal-close`, n.type = "button", n.setAttribute("aria-label", this.messages.filters.sqlFilter.closeLabel), n.innerHTML = "\n      <svg viewBox=\"0 0 16 16\" width=\"14\" height=\"14\" fill=\"currentColor\" aria-hidden=\"true\">\n        <path d=\"M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z\"/>\n      </svg>\n    ", n.addEventListener("click", () => this.close()), t.appendChild(this.titleEl), t.appendChild(n), t;
	}
	createBody() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-sql-filter-modal-body`;
		let n = document.createElement("div");
		n.className = `${e}-sql-filter-modal-section`;
		let r = document.createElement("label");
		r.textContent = this.messages.filters.sqlFilter.labelFieldLabel, this.labelInput = document.createElement("input"), this.labelInput.type = "text", this.labelInput.className = `${e}-filter-input`, this.labelInput.placeholder = this.messages.filters.sqlFilter.labelPlaceholder;
		let i = document.createElement("div");
		i.className = `${e}-sql-filter-modal-hint`, i.textContent = this.messages.filters.sqlFilter.labelHint, n.appendChild(r), n.appendChild(this.labelInput), n.appendChild(i), t.appendChild(n);
		let a = document.createElement("div");
		a.className = `${e}-sql-filter-modal-section`;
		let o = document.createElement("label");
		o.textContent = this.messages.filters.sqlFilter.conditionLabel, this.editorContainer = document.createElement("div"), this.editorContainer.className = `${e}-sql-filter-modal-editor-container`, a.appendChild(o), a.appendChild(this.editorContainer), t.appendChild(a);
		let s = document.createElement("div");
		s.className = `${e}-sql-filter-modal-actions`, this.validateBtn = document.createElement("button"), this.validateBtn.className = `${e}-sql-filter-modal-validate`, this.validateBtn.type = "button", this.validateBtn.textContent = this.messages.common.validate, this.validateBtn.addEventListener("click", () => void this.handleValidate()), this.previewEl = document.createElement("span"), this.previewEl.className = `${e}-sql-filter-modal-preview`, s.appendChild(this.validateBtn), s.appendChild(this.previewEl), t.appendChild(s), this.removeSection = document.createElement("div"), this.removeSection.className = `${e}-sql-filter-modal-remove-section`;
		let c = document.createElement("hr");
		c.className = `${e}-sql-filter-modal-divider`;
		let l = document.createElement("div");
		l.className = `${e}-sql-filter-modal-danger-zone`, this.removeBtn = document.createElement("button"), this.removeBtn.className = `${e}-sql-filter-modal-remove`, this.removeBtn.type = "button", this.removeBtn.textContent = this.messages.filters.sqlFilter.removeButton, this.removeBtn.addEventListener("click", () => {
			this.removeBtn.style.display = "none", this.removeConfirmDiv.style.display = "flex";
		}), this.removeConfirmDiv = document.createElement("div"), this.removeConfirmDiv.className = `${e}-sql-filter-modal-remove-confirm`;
		let u = document.createElement("span");
		u.textContent = this.messages.filters.sqlFilter.removeConfirmText;
		let d = document.createElement("button");
		d.className = `${e}-sql-filter-modal-remove-confirm-btn ${e}-sql-filter-modal-remove-confirm-yes`, d.type = "button", d.textContent = this.messages.common.confirm, d.addEventListener("click", () => this.handleConfirmRemove());
		let f = document.createElement("button");
		return f.className = `${e}-sql-filter-modal-remove-confirm-btn ${e}-sql-filter-modal-remove-confirm-no`, f.type = "button", f.textContent = this.messages.common.cancel, f.addEventListener("click", () => {
			this.removeConfirmDiv.style.display = "none", this.removeBtn.style.display = "";
		}), this.removeConfirmDiv.appendChild(u), this.removeConfirmDiv.appendChild(d), this.removeConfirmDiv.appendChild(f), l.appendChild(this.removeBtn), l.appendChild(this.removeConfirmDiv), this.removeSection.appendChild(c), this.removeSection.appendChild(l), t.appendChild(this.removeSection), t;
	}
	createFooter() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-sql-filter-modal-footer`;
		let n = document.createElement("button");
		return n.className = `${e}-sql-filter-modal-cancel`, n.type = "button", n.textContent = this.messages.common.cancel, n.addEventListener("click", () => this.close()), t.appendChild(n), this.applyBtn = document.createElement("button"), this.applyBtn.className = `${e}-sql-filter-modal-apply`, this.applyBtn.type = "button", this.applyBtn.textContent = this.messages.filters.sqlFilter.applyButton, this.applyBtn.disabled = !0, this.applyBtn.addEventListener("click", () => void this.handleApply()), t.appendChild(this.applyBtn), t;
	}
	ensureEditor() {
		if (this.currentEditor) return;
		let e = this.actions.getCompletionContext();
		this.currentEditor = this.editorFactory ? this.editorFactory(this.editorContainer, e) : new r(this.editorContainer, e, this.prefix, { placeholder: this.messages.filters.sqlFilter.editorPlaceholder }), this.unsubLiveCompletion = i(this.currentEditor, this.state, this.actions), this.removeEditorInputListener(), this.editorInputHandler = () => {
			this.validationVersion++, this.validated = !1, this.previewEl.textContent = "", this.previewEl.style.color = "", this.currentEditor?.setError(null), this.validationAbortController?.abort(), this.validationAbortController = null, this.validateBtn.disabled = !1, this.validateBtn.textContent = this.messages.common.validate, this.updateApplyButtonState();
		}, this.currentEditor.element.addEventListener("input", this.editorInputHandler);
	}
	removeEditorInputListener() {
		this.editorInputHandler && this.currentEditor && (this.currentEditor.element.removeEventListener("input", this.editorInputHandler), this.editorInputHandler = null);
	}
	destroyEditor() {
		this.removeEditorInputListener(), this.unsubLiveCompletion &&= (this.unsubLiveCompletion(), null), this.currentEditor &&= (this.currentEditor.destroy(), null), this.editorContainer.innerHTML = "";
	}
	async handleValidate() {
		if (!this.currentEditor) return;
		let e = this.currentEditor.getValue().trim();
		if (!e) return;
		this.validationAbortController?.abort(), this.validationAbortController = new AbortController();
		let t = ++this.validationVersion;
		this.validateBtn.disabled = !0, this.validateBtn.textContent = this.messages.common.validating, this.currentEditor.setError(null);
		try {
			let n = await this.actions.validateSQLFilter(e, this.validationAbortController.signal);
			if (this.validationVersion !== t) return;
			n.valid ? (this.previewEl.textContent = this.messages.filters.sqlFilter.validationResult(n.matchCount), this.previewEl.style.color = "var(--dt-success)", this.validated = !0) : (this.previewEl.textContent = n.error, this.previewEl.style.color = "var(--dt-error)", this.currentEditor.setError(n.error), this.validated = !1);
		} catch (e) {
			if (this.validationVersion !== t) return;
			let n = e instanceof Error ? e.message : String(e);
			this.previewEl.textContent = n, this.previewEl.style.color = "var(--dt-error)", this.currentEditor.setError(n), this.validated = !1;
		} finally {
			this.validationVersion === t && (this.validateBtn.disabled = !1, this.validateBtn.textContent = this.messages.common.validate, this.updateApplyButtonState());
		}
	}
	async handleApply() {
		if (!this.currentEditor || this.applying) return;
		let e = this.currentEditor.getValue().trim();
		if (!e || !this.validated) return;
		let t = this.labelInput.value.trim() || void 0;
		this.applying = !0, this.updateApplyButtonState();
		try {
			this.currentFilterId === null ? this.actions.addRawSQLFilter(e, t) : this.actions.updateRawSQLFilter(this.currentFilterId, e, t), this.close();
		} finally {
			this.applying = !1;
		}
	}
	handleConfirmRemove() {
		this.currentFilterId !== null && (this.actions.removeRawSQLFilter(this.currentFilterId), this.close());
	}
	updateApplyButtonState() {
		let e = this.currentEditor ? this.currentEditor.getValue().trim() !== "" : !1;
		this.applyBtn.disabled = !e || !this.validated || this.applying;
	}
	open() {
		this.destroyed || this.isOpen || (this.currentFilterId = null, this.titleEl.textContent = this.messages.filters.sqlFilter.createTitle, this.applyBtn.textContent = this.messages.filters.sqlFilter.applyButton, this.removeSection.style.display = "none", this.showModal(this.labelInput));
	}
	openForEdit(e) {
		if (this.destroyed || this.isOpen) return;
		let t = this.state.filters.get(), n = `__raw_sql_${e}__`, r = t.find((e) => e.type === "raw-sql" && e.column === n);
		r && (this.currentFilterId = e, this.titleEl.textContent = this.messages.filters.sqlFilter.editTitle, this.applyBtn.textContent = this.messages.filters.sqlFilter.updateButton, this.removeSection.style.display = "", this.removeBtn.style.display = "", this.removeConfirmDiv.style.display = "none", this.showModal(null, () => {
			this.labelInput.value = r.label ?? "", this.currentEditor && (this.currentEditor.setValue(r.sql), this.currentEditor.focus());
		}));
	}
	showModal(e, t) {
		this.isOpen = !0, this.element.classList.add(`${this.prefix}-sql-filter-modal-backdrop--open`), this.resetForm(), this.ensureEditor(), this.modalHost.open({
			mode: "modal",
			element: this.element,
			dialog: this.dialogEl,
			labelledBy: `${this.prefix}-${this.instanceId}-sql-filter-modal-title`,
			initialFocus: e,
			escapeGuard: () => !!document.querySelector(".cm-tooltip-autocomplete"),
			onClose: () => this.handleHostClose(),
			colorSchemeSource: this.colorSchemeSource
		}), t && t();
	}
	close() {
		this.isOpen && this.modalHost.close();
	}
	handleHostClose() {
		this.isOpen = !1, this.element.classList.remove(`${this.prefix}-sql-filter-modal-backdrop--open`), this.validationAbortController?.abort(), this.validationAbortController = null, this.destroyEditor(), this.currentFilterId = null;
	}
	resetForm() {
		this.labelInput.value = "", this.validated = !1, this.applying = !1, this.previewEl.textContent = "", this.previewEl.style.color = "", this.applyBtn.disabled = !0, this.destroyEditor();
	}
	getElement() {
		return this.element;
	}
	getIsOpen() {
		return this.isOpen;
	}
	destroy() {
		this.destroyed || (this.destroyed = !0, this.close(), this.modalHost.destroy(), this.element.parentNode && this.element.parentNode.removeChild(this.element));
	}
};
//#endregion
export { a as n, o as t };

//# sourceMappingURL=SQLFilterModal-BeUNtaTR.js.map