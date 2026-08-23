# Think Stats — chapter prerequisite map

What depends on what, from CONTENTS.md's prereqs column. Solid arrows are stated dependencies; dashed arrows are inferred (◆-grade, noted on the survey page). Linear order (each chapter leaning on its predecessor) is implied and not drawn.

```yaml map-data
nodes:
  - {id: ch01, label: "1 · Exploratory data", sub: "recited · box 3", title: "Chapter 1 — Exploratory data analysis", col: 0, row: 0, href: "notes/ch01-exploratory.html"}
  - {id: ch02, label: "2 · Distributions", sub: "recited · box 2", title: "Chapter 2 — Distributions", col: 1, row: 0, href: "notes/ch02-distributions.html"}
  - {id: ch03, label: "3 · PMFs", sub: "unread", title: "Chapter 3 — Probability mass functions", col: 2, row: 0, href: ""}
  - {id: ch04, label: "4 · CDFs", sub: "unread", title: "Chapter 4 — Cumulative distribution functions", col: 3, row: 0, href: ""}
  - {id: ch05, label: "5 · Modeling", sub: "unread", title: "Chapter 5 — Modeling distributions", col: 4, row: 0, href: ""}
  - {id: ch06, label: "6 · PDFs", sub: "unread", title: "Chapter 6 — Probability density functions", col: 5, row: 0, href: ""}
  - {id: ch07, label: "7 · Relationships", sub: "unread", title: "Chapter 7 — Relationships between variables", col: 4, row: 1, href: ""}
  - {id: ch08, label: "8 · Estimation", sub: "unread", title: "Chapter 8 — Estimation", col: 5, row: 2, href: ""}
  - {id: ch09, label: "9 · Hypothesis testing", sub: "unread", title: "Chapter 9 — Hypothesis testing", col: 6, row: 1, href: ""}
  - {id: ch10, label: "10 · Least squares", sub: "unread", title: "Chapter 10 — Linear least squares", col: 5, row: 3, href: ""}
  - {id: ch11, label: "11 · Regression", sub: "unread", title: "Chapter 11 — Regression", col: 6, row: 3, href: ""}
  - {id: ch12, label: "12 · Time series", sub: "skimmed", title: "Chapter 12 — Time series analysis", col: 7, row: 3, href: ""}
  - {id: ch13, label: "13 · Survival", sub: "unread", title: "Chapter 13 — Survival analysis", col: 6, row: 2, href: ""}
  - {id: ch14, label: "14 · Analytic methods", sub: "unread", title: "Chapter 14 — Analytic methods", col: 7, row: 1, href: ""}
edges:
  - {from: ch02, to: ch01, label: "NSFG variables", kind: prereq}
  - {from: ch06, to: ch04, label: "framework", kind: prereq}
  - {from: ch06, to: ch05, label: "fitted models", kind: soft}
  - {from: ch07, to: ch02, label: "distributions", kind: prereq}
  - {from: ch07, to: ch04, label: "percentiles", kind: prereq}
  - {from: ch09, to: ch02, label: "first babies again", kind: prereq}
  - {from: ch09, to: ch08, label: "sampling", kind: prereq}
  - {from: ch10, to: ch07, label: "correlation", kind: prereq}
  - {from: ch11, to: ch10, label: "extends", kind: prereq}
  - {from: ch12, to: ch11, label: "regression", kind: prereq}
  - {from: ch13, to: ch04, label: "CDFs", kind: prereq}
  - {from: ch13, to: ch08, label: "estimation", kind: soft}
  - {from: ch14, to: ch08, label: "analytic SEs", kind: prereq}
  - {from: ch14, to: ch09, label: "analytic tests", kind: prereq}
```

Layout logic: reading order flows left to right along the top row; the inference chapters (7–14) fan out below by what they lean on. Arrows point at prerequisites.
