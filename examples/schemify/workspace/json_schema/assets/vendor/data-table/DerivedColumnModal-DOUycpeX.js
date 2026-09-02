import { t as e } from "./rolldown-runtime-Dy4uBu1J.js";
import { X as t, Z as n } from "./VisualizationRegistry-D2a_eV3R.js";
import { t as r } from "./CodeMirrorExpressionEditor-BOO5Hr5e.js";
import { t as i } from "./wireLiveCompletionContext-1rQH1ZoK.js";
//#region src/derived/DerivedColumnModal.ts
var a = /* @__PURE__ */ e({ DerivedColumnModal: () => o }), o = class {
	state;
	actions;
	element;
	dialogEl;
	nameInput;
	nameErrorEl;
	expressionRadio;
	vectorRadio;
	expressionSection;
	vectorSection;
	editorContainer;
	validateBtn;
	typePreview;
	vectorTypeSelect;
	vectorTextarea;
	vectorInfoEl;
	vectorErrorEl;
	errorEl;
	createBtn;
	prefix;
	instanceId;
	messages;
	editorFactory;
	onCreated;
	colorSchemeSource;
	currentEditor = null;
	editorInputHandler = null;
	unsubLiveCompletion = null;
	isOpen = !1;
	destroyed = !1;
	expressionValidated = !1;
	validationVersion = 0;
	creating = !1;
	modalHost = new t();
	constructor(e, t, r) {
		this.state = e, this.actions = t, this.prefix = r?.classPrefix ?? "dt", this.instanceId = r?.instanceId ?? "", this.messages = r?.messages ?? n, this.editorFactory = r?.editorFactory, this.onCreated = r?.onCreated, this.colorSchemeSource = r?.colorSchemeSource, this.element = this.createElement();
	}
	createElement() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-backdrop`;
		let n = document.createElement("div");
		return n.className = `${e}-derived-modal-dialog`, t.appendChild(n), n.appendChild(this.createHeader()), n.appendChild(this.createBody()), n.appendChild(this.createFooter()), this.dialogEl = n, t;
	}
	createHeader() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-header`;
		let n = document.createElement("span");
		n.className = `${e}-derived-modal-title`, n.id = `${e}-${this.instanceId}-derived-modal-title`, n.textContent = this.messages.derived.newColumnTitle;
		let r = document.createElement("button");
		return r.className = `${e}-derived-modal-close`, r.type = "button", r.setAttribute("aria-label", this.messages.derived.closeLabel), r.innerHTML = "\n      <svg viewBox=\"0 0 16 16\" width=\"14\" height=\"14\" fill=\"currentColor\" aria-hidden=\"true\">\n        <path d=\"M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z\"/>\n      </svg>\n    ", r.addEventListener("click", () => this.close()), t.appendChild(n), t.appendChild(r), t;
	}
	createBody() {
		let e = this.prefix, t = document.createElement("div");
		return t.className = `${e}-derived-modal-body`, t.appendChild(this.createNameSection()), t.appendChild(this.createModeToggle()), this.expressionSection = this.createExpressionSection(), t.appendChild(this.expressionSection), this.vectorSection = this.createVectorSection(), this.vectorSection.style.display = "none", t.appendChild(this.vectorSection), this.errorEl = document.createElement("div"), this.errorEl.className = `${e}-derived-modal-error`, this.errorEl.style.display = "none", t.appendChild(this.errorEl), t;
	}
	createNameSection() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-section`;
		let n = document.createElement("label");
		return n.textContent = this.messages.derived.nameLabel, t.appendChild(n), this.nameInput = document.createElement("input"), this.nameInput.type = "text", this.nameInput.className = `${e}-filter-input`, this.nameInput.placeholder = this.messages.derived.namePlaceholder, this.nameInput.autocomplete = "off", this.nameInput.spellcheck = !1, this.nameInput.addEventListener("input", () => {
			this.validateName(), this.updateCreateButtonState();
		}), t.appendChild(this.nameInput), this.nameErrorEl = document.createElement("div"), this.nameErrorEl.className = `${e}-derived-modal-name-error`, this.nameErrorEl.style.display = "none", t.appendChild(this.nameErrorEl), t;
	}
	createModeToggle() {
		let e = this.prefix, t = document.createElement("fieldset");
		t.className = `${e}-derived-modal-mode-group`;
		let n = document.createElement("legend");
		n.textContent = this.messages.derived.typeLabel, t.appendChild(n);
		let r = document.createElement("label");
		r.className = `${e}-derived-modal-mode-option`, this.expressionRadio = document.createElement("input"), this.expressionRadio.type = "radio", this.expressionRadio.name = `${e}-derived-modal-mode`, this.expressionRadio.value = "expression", this.expressionRadio.checked = !0, this.expressionRadio.addEventListener("change", () => this.onModeChange("expression")), r.appendChild(this.expressionRadio), r.appendChild(document.createTextNode(this.messages.derived.expressionModeLabel)), t.appendChild(r);
		let i = document.createElement("label");
		return i.className = `${e}-derived-modal-mode-option`, this.vectorRadio = document.createElement("input"), this.vectorRadio.type = "radio", this.vectorRadio.name = `${e}-derived-modal-mode`, this.vectorRadio.value = "vector", this.vectorRadio.addEventListener("change", () => this.onModeChange("vector")), i.appendChild(this.vectorRadio), i.appendChild(document.createTextNode(this.messages.derived.vectorModeLabel)), t.appendChild(i), t;
	}
	createExpressionSection() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-section`;
		let n = document.createElement("label");
		n.textContent = this.messages.derived.expressionLabel, t.appendChild(n), this.editorContainer = document.createElement("div"), this.editorContainer.className = `${e}-derived-modal-editor-container`, t.appendChild(this.editorContainer);
		let r = document.createElement("div");
		return r.className = `${e}-derived-modal-expr-actions`, this.validateBtn = document.createElement("button"), this.validateBtn.className = `${e}-derived-modal-validate`, this.validateBtn.type = "button", this.validateBtn.textContent = this.messages.common.validate, this.validateBtn.addEventListener("click", () => void this.handleValidateExpression()), r.appendChild(this.validateBtn), this.typePreview = document.createElement("span"), this.typePreview.className = `${e}-derived-modal-type-preview`, r.appendChild(this.typePreview), t.appendChild(r), t;
	}
	createVectorSection() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-section`;
		let n = document.createElement("label");
		n.textContent = this.messages.derived.vectorTypeLabel, t.appendChild(n), this.vectorTypeSelect = document.createElement("select"), this.vectorTypeSelect.className = `${e}-filter-select`;
		for (let e of [
			"integer",
			"float",
			"decimal",
			"string",
			"boolean",
			"uuid",
			"date",
			"timestamp",
			"time",
			"interval"
		]) {
			let t = document.createElement("option");
			t.value = e, t.textContent = e, this.vectorTypeSelect.appendChild(t);
		}
		this.vectorTypeSelect.addEventListener("change", () => {
			this.validateVectorValues(), this.updateCreateButtonState();
		}), t.appendChild(this.vectorTypeSelect);
		let r = document.createElement("label");
		return r.textContent = this.messages.derived.vectorValuesLabel, r.style.marginTop = "0.5rem", t.appendChild(r), this.vectorTextarea = document.createElement("textarea"), this.vectorTextarea.className = `${e}-derived-modal-vector-textarea`, this.vectorTextarea.rows = 8, this.vectorTextarea.placeholder = this.messages.derived.vectorPlaceholder, this.vectorTextarea.spellcheck = !1, this.vectorTextarea.addEventListener("input", () => {
			this.updateVectorInfo(), this.validateVectorValues(), this.updateCreateButtonState();
		}), t.appendChild(this.vectorTextarea), this.vectorInfoEl = document.createElement("div"), this.vectorInfoEl.className = `${e}-derived-modal-vector-info`, t.appendChild(this.vectorInfoEl), this.vectorErrorEl = document.createElement("div"), this.vectorErrorEl.className = `${e}-derived-modal-vector-error`, this.vectorErrorEl.style.display = "none", t.appendChild(this.vectorErrorEl), t;
	}
	createFooter() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-modal-footer`;
		let n = document.createElement("button");
		return n.className = `${e}-derived-modal-cancel`, n.type = "button", n.textContent = this.messages.common.cancel, n.addEventListener("click", () => this.close()), t.appendChild(n), this.createBtn = document.createElement("button"), this.createBtn.className = `${e}-derived-modal-create`, this.createBtn.type = "button", this.createBtn.textContent = this.messages.derived.createButton, this.createBtn.disabled = !0, this.createBtn.addEventListener("click", () => void this.handleCreate()), t.appendChild(this.createBtn), t;
	}
	onModeChange(e) {
		e === "expression" ? (this.expressionSection.style.display = "", this.vectorSection.style.display = "none", this.ensureEditor()) : (this.expressionSection.style.display = "none", this.vectorSection.style.display = "", this.updateVectorInfo()), this.expressionValidated = !1, this.typePreview.textContent = "", this.typePreview.style.color = "", this.vectorErrorEl.style.display = "none", this.vectorErrorEl.textContent = "", this.errorEl.style.display = "none", this.updateCreateButtonState();
	}
	getCurrentMode() {
		return this.vectorRadio.checked ? "vector" : "expression";
	}
	validateName() {
		let e = this.nameInput.value.trim();
		if (!e) {
			this.nameErrorEl.textContent = this.messages.derived.nameRequired, this.nameErrorEl.style.display = "";
			return;
		}
		this.state.schema.get().find((t) => t.name === e) ? (this.nameErrorEl.textContent = this.messages.derived.nameDuplicate(e), this.nameErrorEl.style.display = "") : (this.nameErrorEl.textContent = "", this.nameErrorEl.style.display = "none");
	}
	isNameValid() {
		let e = this.nameInput.value.trim();
		return e ? !this.state.schema.get().some((t) => t.name === e) : !1;
	}
	updateVectorInfo() {
		let e = this.getVectorLines().length, t = this.state.totalRows.get();
		this.vectorInfoEl.textContent = this.messages.derived.vectorInfo(e, t);
	}
	validateVectorValues() {
		let e = this.getVectorLines();
		if (e.length === 0) {
			this.vectorErrorEl.style.display = "none";
			return;
		}
		let t = this.state.totalRows.get();
		if (e.length !== t) {
			this.vectorErrorEl.textContent = this.messages.derived.vectorCountMismatch(t, e.length), this.vectorErrorEl.style.display = "";
			return;
		}
		let n = this.vectorTypeSelect.value, r = this.parseVectorValues(e, n);
		r.success ? (this.vectorErrorEl.textContent = "", this.vectorErrorEl.style.display = "none") : (this.vectorErrorEl.textContent = r.error, this.vectorErrorEl.style.display = "");
	}
	isVectorValid() {
		let e = this.getVectorLines(), t = this.state.totalRows.get();
		if (e.length !== t || t === 0) return !1;
		let n = this.vectorTypeSelect.value;
		return this.parseVectorValues(e, n).success;
	}
	getVectorLines() {
		let e = this.vectorTextarea.value;
		if (!e.trim()) return [];
		let t = e.split("\n");
		for (; t.length > 0 && t[t.length - 1].trim() === "";) t.pop();
		return t.map((e) => e.trim());
	}
	updateCreateButtonState() {
		let e = this.isNameValid();
		this.getCurrentMode() === "expression" ? this.createBtn.disabled = !e || !this.expressionValidated || this.creating : this.createBtn.disabled = !e || !this.isVectorValid() || this.creating;
	}
	async handleValidateExpression() {
		if (!this.currentEditor) return;
		let e = this.currentEditor.getValue().trim();
		if (!e) {
			this.currentEditor.setError(this.messages.derived.expressionRequired);
			return;
		}
		let t = ++this.validationVersion;
		this.validateBtn.disabled = !0, this.validateBtn.textContent = this.messages.common.validating;
		try {
			let n = await this.actions.validateExpression(e);
			if (this.validationVersion !== t) return;
			n.valid ? (this.typePreview.textContent = this.messages.derived.typePreview(n.type, n.originalType), this.typePreview.style.color = "var(--dt-success)", this.expressionValidated = !0, this.currentEditor.setError(null)) : (this.typePreview.textContent = n.error ?? this.messages.derived.validationFailed, this.typePreview.style.color = "var(--dt-error)", this.expressionValidated = !1, this.currentEditor.setError(n.error ?? this.messages.derived.validationFailed));
		} catch (e) {
			if (this.validationVersion !== t) return;
			let n = e instanceof Error ? e.message : String(e);
			this.typePreview.textContent = n, this.typePreview.style.color = "var(--dt-error)", this.expressionValidated = !1, this.currentEditor.setError(n);
		} finally {
			this.validationVersion === t && (this.validateBtn.disabled = !1, this.validateBtn.textContent = this.messages.common.validate, this.updateCreateButtonState());
		}
	}
	async handleCreate() {
		if (this.creating) return;
		let e = this.nameInput.value.trim();
		if (!e) return;
		let t;
		if (this.getCurrentMode() === "expression") {
			let n = this.currentEditor?.getValue().trim() ?? "";
			if (!n) return;
			t = {
				kind: "expression",
				name: e,
				expression: n
			};
		} else {
			let n = this.vectorTypeSelect.value, r = this.getVectorLines(), i = this.parseVectorValues(r, n);
			if (!i.success) {
				this.vectorErrorEl.textContent = i.error, this.vectorErrorEl.style.display = "";
				return;
			}
			t = {
				kind: "vector",
				name: e,
				vectorType: n,
				values: i.values
			};
		}
		this.creating = !0, this.createBtn.disabled = !0, this.createBtn.textContent = this.messages.common.creating, this.errorEl.style.display = "none";
		try {
			let e = await this.actions.addDerivedColumn(t);
			e.success ? (this.close(), this.onCreated?.()) : (this.errorEl.textContent = e.error ?? this.messages.derived.createFailed, this.errorEl.style.display = "");
		} catch (e) {
			let t = e instanceof Error ? e.message : String(e);
			this.errorEl.textContent = t, this.errorEl.style.display = "";
		} finally {
			this.creating = !1, this.createBtn.textContent = this.messages.derived.createButton, this.updateCreateButtonState();
		}
	}
	parseVectorValues(e, t) {
		let n = this.messages.derived;
		if (t === "string") return {
			success: !0,
			values: e
		};
		if (t === "boolean") {
			let t = [];
			for (let r = 0; r < e.length; r++) {
				let i = e[r].toLowerCase();
				if (i === "true" || i === "1") t.push(!0);
				else if (i === "false" || i === "0") t.push(!1);
				else return {
					success: !1,
					error: n.vectorInvalidBoolean(r + 1, e[r])
				};
			}
			return {
				success: !0,
				values: t
			};
		}
		if (t === "date") {
			let t = /^\d{4}-\d{2}-\d{2}$/, r = [];
			for (let i = 0; i < e.length; i++) {
				if (!t.test(e[i])) return {
					success: !1,
					error: n.vectorInvalidDate(i + 1, e[i])
				};
				r.push(e[i]);
			}
			return {
				success: !0,
				values: r
			};
		}
		if (t === "timestamp") {
			let t = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/, r = [];
			for (let i = 0; i < e.length; i++) {
				if (!t.test(e[i])) return {
					success: !1,
					error: n.vectorInvalidTimestamp(i + 1, e[i])
				};
				r.push(e[i]);
			}
			return {
				success: !0,
				values: r
			};
		}
		if (t === "time") {
			let t = /^\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/, r = [];
			for (let i = 0; i < e.length; i++) {
				if (!t.test(e[i])) return {
					success: !1,
					error: n.vectorInvalidTime(i + 1, e[i])
				};
				r.push(e[i]);
			}
			return {
				success: !0,
				values: r
			};
		}
		if (t === "interval") {
			let t = [];
			for (let r = 0; r < e.length; r++) {
				if (e[r].trim().length === 0) return {
					success: !1,
					error: n.vectorInvalidInterval(r + 1)
				};
				t.push(e[r]);
			}
			return {
				success: !0,
				values: t
			};
		}
		if (t === "decimal") {
			let t = /^-?\d+(\.\d+)?$/, r = [];
			for (let i = 0; i < e.length; i++) {
				if (!t.test(e[i])) return {
					success: !1,
					error: n.vectorInvalidDecimal(i + 1, e[i])
				};
				r.push(e[i]);
			}
			return {
				success: !0,
				values: r
			};
		}
		if (t === "uuid") {
			let t = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, r = [];
			for (let i = 0; i < e.length; i++) {
				if (!t.test(e[i])) return {
					success: !1,
					error: n.vectorInvalidUUID(i + 1, e[i])
				};
				r.push(e[i]);
			}
			return {
				success: !0,
				values: r
			};
		}
		let r = [];
		for (let i = 0; i < e.length; i++) if (t === "integer") {
			if (!/^-?\d+$/.test(e[i])) return {
				success: !1,
				error: n.vectorInvalidInteger(i + 1, e[i])
			};
			let t = parseInt(e[i], 10);
			if (isNaN(t)) return {
				success: !1,
				error: n.vectorInvalidInteger(i + 1, e[i])
			};
			r.push(t);
		} else {
			let t = parseFloat(e[i]);
			if (isNaN(t) || !Number.isFinite(t)) return {
				success: !1,
				error: n.vectorInvalidFloat(i + 1, e[i])
			};
			r.push(t);
		}
		return {
			success: !0,
			values: r
		};
	}
	ensureEditor() {
		if (this.currentEditor) return;
		let e = this.actions.getCompletionContext();
		this.currentEditor = this.editorFactory ? this.editorFactory(this.editorContainer, e) : new r(this.editorContainer, e, this.prefix), this.unsubLiveCompletion = i(this.currentEditor, this.state, this.actions), this.removeEditorInputListener(), this.editorInputHandler = () => {
			this.validationVersion++, this.expressionValidated = !1, this.typePreview.textContent = "", this.typePreview.style.color = "", this.updateCreateButtonState();
		}, this.currentEditor.element.addEventListener("input", this.editorInputHandler);
	}
	removeEditorInputListener() {
		this.editorInputHandler && this.currentEditor && (this.currentEditor.element.removeEventListener("input", this.editorInputHandler), this.editorInputHandler = null);
	}
	destroyEditor() {
		this.removeEditorInputListener(), this.unsubLiveCompletion &&= (this.unsubLiveCompletion(), null), this.currentEditor &&= (this.currentEditor.destroy(), null), this.editorContainer.innerHTML = "";
	}
	open() {
		this.destroyed || this.isOpen || (this.isOpen = !0, this.element.classList.add(`${this.prefix}-derived-modal-backdrop--open`), this.resetForm(), this.ensureEditor(), this.modalHost.open({
			mode: "modal",
			element: this.element,
			dialog: this.dialogEl,
			labelledBy: `${this.prefix}-${this.instanceId}-derived-modal-title`,
			initialFocus: this.nameInput,
			escapeGuard: () => !!document.querySelector(".cm-tooltip-autocomplete"),
			onClose: () => this.handleHostClose(),
			colorSchemeSource: this.colorSchemeSource
		}));
	}
	close() {
		this.isOpen && this.modalHost.close();
	}
	handleHostClose() {
		this.isOpen = !1, this.element.classList.remove(`${this.prefix}-derived-modal-backdrop--open`), this.destroyEditor();
	}
	resetForm() {
		this.nameInput.value = "", this.nameErrorEl.textContent = "", this.nameErrorEl.style.display = "none", this.expressionRadio.checked = !0, this.vectorRadio.checked = !1, this.expressionSection.style.display = "", this.vectorSection.style.display = "none", this.destroyEditor(), this.expressionValidated = !1, this.typePreview.textContent = "", this.typePreview.style.color = "", this.vectorTypeSelect.value = "integer", this.vectorTextarea.value = "", this.vectorErrorEl.textContent = "", this.vectorErrorEl.style.display = "none", this.updateVectorInfo(), this.errorEl.textContent = "", this.errorEl.style.display = "none", this.creating = !1, this.createBtn.textContent = this.messages.derived.createButton, this.createBtn.disabled = !0;
	}
	getElement() {
		return this.element;
	}
	getIsOpen() {
		return this.isOpen;
	}
	destroy() {
		this.destroyed || (this.destroyed = !0, this.close(), this.modalHost.destroy(), this.destroyEditor(), this.element.parentNode && this.element.parentNode.removeChild(this.element));
	}
};
//#endregion
export { a as n, o as t };

//# sourceMappingURL=DerivedColumnModal-DOUycpeX.js.map