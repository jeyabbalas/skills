import { t as e } from "./rolldown-runtime-Dy4uBu1J.js";
import { X as t, Z as n } from "./VisualizationRegistry-D2a_eV3R.js";
import { t as r } from "./CodeMirrorExpressionEditor-BOO5Hr5e.js";
//#region src/derived/DerivedColumnEditPanel.ts
var i = /* @__PURE__ */ e({ DerivedColumnEditPanel: () => a }), a = class {
	state;
	actions;
	element;
	titleEl;
	nameInput;
	nameErrorEl;
	expressionSection;
	vectorInfoSection;
	vectorInfoText;
	editorContainer;
	validateBtn;
	typePreview;
	updateBtn;
	deleteBtn;
	deleteConfirmDiv;
	prefix;
	messages;
	editorFactory;
	colorSchemeSource;
	currentEditor = null;
	currentColumn = null;
	currentDef = null;
	currentAnchor = null;
	isOpen = !1;
	destroyed = !1;
	expressionValidated = !1;
	validationVersion = 0;
	updating = !1;
	modalHost = new t();
	editorInputHandler = null;
	unsubscribe = null;
	constructor(e, t, r) {
		this.state = e, this.actions = t, this.prefix = r?.classPrefix ?? "dt", this.messages = r?.messages ?? n, this.editorFactory = r?.editorFactory, this.colorSchemeSource = r?.colorSchemeSource, this.element = this.createElement(), this.titleEl = this.element.querySelector(`.${this.prefix}-derived-edit-title`), this.nameInput = this.element.querySelector(`.${this.prefix}-derived-edit-name-input`), this.nameErrorEl = this.element.querySelector(`.${this.prefix}-derived-edit-name-error`), this.expressionSection = this.element.querySelector(`.${this.prefix}-derived-edit-expr-section`), this.vectorInfoSection = this.element.querySelector(`.${this.prefix}-derived-edit-vector-section`), this.vectorInfoText = this.element.querySelector(`.${this.prefix}-derived-edit-vector-text`), this.editorContainer = this.element.querySelector(`.${this.prefix}-derived-edit-editor-container`), this.validateBtn = this.element.querySelector(`.${this.prefix}-derived-edit-validate`), this.typePreview = this.element.querySelector(`.${this.prefix}-derived-edit-type-preview`), this.updateBtn = this.element.querySelector(`.${this.prefix}-derived-edit-update`), this.deleteBtn = this.element.querySelector(`.${this.prefix}-derived-edit-delete`), this.deleteConfirmDiv = this.element.querySelector(`.${this.prefix}-derived-edit-delete-confirm`), this.attachEventListeners(), this.unsubscribe = this.state.derivedColumns.subscribe(() => {
			!this.destroyed && this.isOpen && this.currentColumn && (this.state.derivedColumns.get().some((e) => e.name === this.currentColumn) || this.close());
		});
	}
	createElement() {
		let e = this.prefix, t = document.createElement("div");
		t.className = `${e}-derived-edit-panel`, t.style.display = "none", t.setAttribute("role", "dialog");
		let n = document.createElement("div");
		n.className = `${e}-derived-edit-header`;
		let r = document.createElement("span");
		r.className = `${e}-derived-edit-title`, r.textContent = this.messages.derived.editTitle;
		let i = document.createElement("button");
		i.className = `${e}-derived-edit-close`, i.type = "button", i.setAttribute("aria-label", this.messages.derived.closeEditLabel), i.innerHTML = "\n      <svg viewBox=\"0 0 16 16\" width=\"14\" height=\"14\" fill=\"currentColor\" aria-hidden=\"true\">\n        <path d=\"M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z\"/>\n      </svg>\n    ", n.appendChild(r), n.appendChild(i), t.appendChild(n);
		let a = document.createElement("div");
		a.className = `${e}-derived-edit-body`;
		let o = document.createElement("div");
		o.className = `${e}-derived-edit-section`;
		let s = document.createElement("label");
		s.textContent = this.messages.derived.nameLabel;
		let c = document.createElement("input");
		c.type = "text", c.className = `${e}-filter-input ${e}-derived-edit-name-input`, c.autocomplete = "off", c.spellcheck = !1;
		let l = document.createElement("div");
		l.className = `${e}-derived-edit-name-error`, o.appendChild(s), o.appendChild(c), o.appendChild(l), a.appendChild(o);
		let u = document.createElement("div");
		u.className = `${e}-derived-edit-section ${e}-derived-edit-expr-section`;
		let d = document.createElement("label");
		d.textContent = this.messages.derived.expressionLabel;
		let f = document.createElement("div");
		f.className = `${e}-derived-edit-editor-container`, u.appendChild(d), u.appendChild(f), a.appendChild(u);
		let p = document.createElement("div");
		p.className = `${e}-derived-edit-section ${e}-derived-edit-vector-section`, p.style.display = "none";
		let m = document.createElement("label");
		m.textContent = this.messages.derived.infoLabel;
		let h = document.createElement("div");
		h.className = `${e}-derived-edit-vector-text`, p.appendChild(m), p.appendChild(h), a.appendChild(p);
		let g = document.createElement("div");
		g.className = `${e}-derived-edit-actions`;
		let _ = document.createElement("button");
		_.className = `${e}-derived-edit-validate`, _.type = "button", _.textContent = this.messages.common.validate;
		let v = document.createElement("span");
		v.className = `${e}-derived-edit-type-preview`;
		let y = document.createElement("button");
		y.className = `${e}-derived-edit-update`, y.type = "button", y.textContent = this.messages.common.update, y.disabled = !0, g.appendChild(_), g.appendChild(v), g.appendChild(y), a.appendChild(g);
		let b = document.createElement("hr");
		b.className = `${e}-derived-edit-divider`, a.appendChild(b);
		let x = document.createElement("div");
		x.className = `${e}-derived-edit-danger-zone`;
		let S = document.createElement("button");
		S.className = `${e}-derived-edit-delete`, S.type = "button", S.textContent = this.messages.derived.deleteButton;
		let C = document.createElement("div");
		C.className = `${e}-derived-edit-delete-confirm`;
		let w = document.createElement("span");
		w.textContent = this.messages.common.deleteConfirm;
		let T = document.createElement("button");
		T.className = `${e}-derived-edit-delete-confirm-btn ${e}-derived-edit-delete-confirm-yes`, T.type = "button", T.textContent = this.messages.common.confirm;
		let E = document.createElement("button");
		return E.className = `${e}-derived-edit-delete-confirm-btn ${e}-derived-edit-delete-confirm-no`, E.type = "button", E.textContent = this.messages.common.cancel, C.appendChild(w), C.appendChild(T), C.appendChild(E), x.appendChild(S), x.appendChild(C), a.appendChild(x), t.appendChild(a), t;
	}
	attachEventListeners() {
		this.element.querySelector(`.${this.prefix}-derived-edit-close`).addEventListener("click", () => this.close()), this.nameInput.addEventListener("input", () => {
			this.validateName(), this.updateButtonState();
		}), this.validateBtn.addEventListener("click", () => void this.handleValidate()), this.updateBtn.addEventListener("click", () => void this.handleUpdate()), this.deleteBtn.addEventListener("click", () => {
			this.deleteBtn.style.display = "none", this.deleteConfirmDiv.style.display = "flex";
		}), this.deleteConfirmDiv.querySelector(`.${this.prefix}-derived-edit-delete-confirm-yes`).addEventListener("click", () => void this.handleConfirmDelete()), this.deleteConfirmDiv.querySelector(`.${this.prefix}-derived-edit-delete-confirm-no`).addEventListener("click", () => {
			this.deleteConfirmDiv.style.display = "none", this.deleteBtn.style.display = "";
		});
	}
	position(e) {
		let t = this.element.parentElement;
		if (!t) return;
		let n = t.getBoundingClientRect(), r = e.getBoundingClientRect(), i = r.left - n.left, a = r.bottom - n.top + 4, o = this.element.offsetWidth || 360;
		i + o > n.width && (i = Math.max(0, n.width - o)), this.element.style.left = `${i}px`, this.element.style.top = `${a}px`;
	}
	toggle(e, t) {
		this.isOpen && this.currentColumn === e ? this.close() : this.open(e, t);
	}
	open(e, t) {
		if (this.destroyed) return;
		let n = this.state.derivedColumns.get().find((t) => t.name === e);
		if (!n) return;
		let i = this.state.schema.get().find((t) => t.name === e);
		if (this.currentColumn !== e && this.destroyEditor(), this.currentColumn = e, this.currentDef = n, this.currentAnchor && this.currentAnchor.classList.remove(`${this.prefix}-derived-icon-btn--active`), this.currentAnchor = t, t.classList.add(`${this.prefix}-derived-icon-btn--active`), this.titleEl.textContent = this.messages.derived.editTitleForColumn(e), this.nameInput.value = n.name, this.nameErrorEl.textContent = "", this.nameErrorEl.style.display = "none", this.typePreview.textContent = "", this.typePreview.style.color = "", this.deleteBtn.style.display = "", this.deleteConfirmDiv.style.display = "none", n.kind === "expression") {
			if (this.expressionSection.style.display = "", this.vectorInfoSection.style.display = "none", this.validateBtn.style.display = "", !this.currentEditor) {
				let e = this.actions.getCompletionContext();
				this.currentEditor = this.editorFactory ? this.editorFactory(this.editorContainer, e) : new r(this.editorContainer, e, this.prefix);
			}
			this.currentEditor.setValue(n.expression), this.currentEditor.setError(null), this.removeEditorInputListener(), this.editorInputHandler = () => {
				this.validationVersion++, this.expressionValidated = !1, this.typePreview.textContent = "", this.typePreview.style.color = "", this.updateButtonState();
			}, this.currentEditor.element.addEventListener("input", this.editorInputHandler), this.expressionValidated = !1;
		} else {
			this.expressionSection.style.display = "none", this.vectorInfoSection.style.display = "", this.validateBtn.style.display = "none";
			let e = i?.originalType ?? n.vectorType;
			this.vectorInfoText.textContent = this.messages.derived.vectorInfoText(e, n.values.length), this.expressionValidated = !0;
		}
		this.updateButtonState(), this.isOpen = !0, this.element.style.display = "", this.position(t), this.modalHost.open({
			mode: "panel",
			element: this.element,
			outsideClickIgnore: [`.${this.prefix}-derived-icon-btn`],
			escapeGuard: () => !!document.querySelector(".cm-tooltip-autocomplete"),
			initialFocus: this.nameInput,
			onClose: () => this.handleHostClose(),
			colorSchemeSource: this.colorSchemeSource
		});
	}
	close() {
		this.isOpen && this.modalHost.close();
	}
	handleHostClose() {
		this.isOpen = !1, this.currentAnchor &&= (this.currentAnchor.classList.remove(`${this.prefix}-derived-icon-btn--active`), null), this.element.style.display = "none";
	}
	validateName() {
		let e = this.nameInput.value.trim();
		if (!e) {
			this.nameErrorEl.textContent = this.messages.derived.nameRequired, this.nameErrorEl.style.display = "";
			return;
		}
		this.state.schema.get().find((t) => t.name === e && t.name !== this.currentColumn) ? (this.nameErrorEl.textContent = this.messages.derived.nameDuplicate(e), this.nameErrorEl.style.display = "") : (this.nameErrorEl.textContent = "", this.nameErrorEl.style.display = "none");
	}
	isNameValid() {
		let e = this.nameInput.value.trim();
		return e ? !this.state.schema.get().some((t) => t.name === e && t.name !== this.currentColumn) : !1;
	}
	updateButtonState() {
		this.currentDef?.kind === "expression" ? this.updateBtn.disabled = !this.isNameValid() || !this.expressionValidated || this.updating : this.updateBtn.disabled = !this.isNameValid() || this.updating;
	}
	async handleValidate() {
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
			n.valid ? (this.typePreview.textContent = this.messages.derived.typePreview(n.type, n.originalType), this.typePreview.style.color = "", this.expressionValidated = !0, this.currentEditor.setError(null)) : (this.typePreview.textContent = n.error ?? this.messages.derived.validationFailed, this.typePreview.style.color = "var(--dt-error)", this.expressionValidated = !1, this.currentEditor.setError(n.error ?? this.messages.derived.validationFailed));
		} catch (e) {
			if (this.validationVersion !== t) return;
			let n = e instanceof Error ? e.message : String(e);
			this.typePreview.textContent = n, this.typePreview.style.color = "var(--dt-error)", this.expressionValidated = !1, this.currentEditor.setError(n);
		} finally {
			this.validationVersion === t && (this.validateBtn.disabled = !1, this.validateBtn.textContent = this.messages.common.validate, this.updateButtonState());
		}
	}
	async handleUpdate() {
		if (!this.currentColumn || !this.currentDef || this.updating) return;
		let e = this.nameInput.value.trim(), t = this.currentColumn, n;
		n = this.currentDef.kind === "expression" ? {
			kind: "expression",
			name: e,
			expression: this.currentEditor?.getValue().trim() ?? ""
		} : {
			kind: "vector",
			name: e,
			vectorType: this.currentDef.vectorType,
			values: this.currentDef.values
		}, this.updating = !0, this.updateBtn.disabled = !0, this.updateBtn.textContent = this.messages.common.updating;
		try {
			let e = await this.actions.updateDerivedColumn(t, n);
			e.success ? this.close() : (this.typePreview.textContent = e.error ?? this.messages.derived.updateFailed, this.typePreview.style.color = "var(--dt-error)");
		} catch (e) {
			let t = e instanceof Error ? e.message : String(e);
			this.typePreview.textContent = t, this.typePreview.style.color = "var(--dt-error)";
		} finally {
			this.updating = !1, this.updateBtn.textContent = this.messages.common.update, this.updateButtonState();
		}
	}
	async handleConfirmDelete() {
		if (this.currentColumn) try {
			await this.actions.removeDerivedColumn(this.currentColumn), this.close();
		} catch (e) {
			let t = e instanceof Error ? e.message : String(e);
			this.typePreview.textContent = this.messages.derived.deleteFailed(t), this.typePreview.style.color = "var(--dt-error)", this.deleteConfirmDiv.style.display = "none", this.deleteBtn.style.display = "";
		}
	}
	removeEditorInputListener() {
		this.editorInputHandler && this.currentEditor && (this.currentEditor.element.removeEventListener("input", this.editorInputHandler), this.editorInputHandler = null);
	}
	destroyEditor() {
		this.removeEditorInputListener(), this.currentEditor &&= (this.currentEditor.destroy(), null), this.editorContainer.innerHTML = "";
	}
	getElement() {
		return this.element;
	}
	getIsOpen() {
		return this.isOpen;
	}
	getCurrentColumn() {
		return this.isOpen ? this.currentColumn : null;
	}
	destroy() {
		this.destroyed || (this.destroyed = !0, this.close(), this.modalHost.destroy(), this.unsubscribe &&= (this.unsubscribe(), null), this.destroyEditor(), this.element.parentNode && this.element.parentNode.removeChild(this.element));
	}
};
//#endregion
export { i as n, a as t };

//# sourceMappingURL=DerivedColumnEditPanel-DYb9GbYR.js.map