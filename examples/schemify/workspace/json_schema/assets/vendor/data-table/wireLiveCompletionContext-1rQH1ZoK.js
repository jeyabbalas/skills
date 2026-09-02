//#region src/sql-editor/wireLiveCompletionContext.ts
function e(e, t, n) {
	let r = !1, i = !1, a = () => {
		r || i || (r = !0, queueMicrotask(() => {
			if (r = !1, !i) try {
				e.updateCompletionContext(n.getCompletionContext());
			} catch {}
		}));
	}, o = t.schema.subscribe(a), s = t.derivedColumns.subscribe(a);
	return () => {
		i = !0, o(), s();
	};
}
//#endregion
export { e as t };

//# sourceMappingURL=wireLiveCompletionContext-1rQH1ZoK.js.map