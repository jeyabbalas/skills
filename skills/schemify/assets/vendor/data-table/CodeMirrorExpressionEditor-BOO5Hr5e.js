import { autocompletion as e } from "@codemirror/autocomplete";
import { defaultKeymap as t, history as n, historyKeymap as r } from "@codemirror/commands";
import { Compartment as i, EditorState as a } from "@codemirror/state";
import { EditorView as o, keymap as s, placeholder as c } from "@codemirror/view";
import { PostgreSQL as l, sql as u } from "@codemirror/lang-sql";
import { HighlightStyle as d, syntaxHighlighting as f } from "@codemirror/language";
import { tags as p } from "@lezer/highlight";
//#region src/sql-editor/duckdbFunctionDetails.ts
var m = Object.freeze([
	Object.freeze({
		name: "avg",
		category: "aggregate",
		description: "Arithmetic mean of all non-null values."
	}),
	Object.freeze({
		name: "count",
		category: "aggregate",
		description: "Number of non-null values; count(*) counts rows."
	}),
	Object.freeze({
		name: "count_star",
		category: "aggregate",
		description: "Number of input rows, including those with NULLs."
	}),
	Object.freeze({
		name: "first",
		category: "aggregate",
		description: "First non-null value encountered in the group."
	}),
	Object.freeze({
		name: "last",
		category: "aggregate",
		description: "Last non-null value encountered in the group."
	}),
	Object.freeze({
		name: "max",
		category: "aggregate",
		description: "Largest non-null value in the group."
	}),
	Object.freeze({
		name: "min",
		category: "aggregate",
		description: "Smallest non-null value in the group."
	}),
	Object.freeze({
		name: "sum",
		category: "aggregate",
		description: "Sum of all non-null numeric values."
	}),
	Object.freeze({
		name: "string_agg",
		category: "aggregate",
		description: "Concatenate string values with an optional separator."
	}),
	Object.freeze({
		name: "list_agg",
		category: "aggregate",
		description: "Aggregate values into a list (alias for list())."
	}),
	Object.freeze({
		name: "group_concat",
		category: "aggregate",
		description: "Concatenate group values into a single string."
	}),
	Object.freeze({
		name: "approx_count_distinct",
		category: "aggregate",
		description: "Approximate distinct count using HyperLogLog."
	}),
	Object.freeze({
		name: "approx_quantile",
		category: "aggregate",
		description: "Approximate quantile via t-digest."
	}),
	Object.freeze({
		name: "median",
		category: "aggregate",
		description: "Median (50th percentile) of the values."
	}),
	Object.freeze({
		name: "mode",
		category: "aggregate",
		description: "Most frequent value in the group."
	}),
	Object.freeze({
		name: "stddev",
		category: "aggregate",
		description: "Sample standard deviation (alias for stddev_samp)."
	}),
	Object.freeze({
		name: "stddev_pop",
		category: "aggregate",
		description: "Population standard deviation."
	}),
	Object.freeze({
		name: "stddev_samp",
		category: "aggregate",
		description: "Sample standard deviation."
	}),
	Object.freeze({
		name: "variance",
		category: "aggregate",
		description: "Sample variance (alias for var_samp)."
	}),
	Object.freeze({
		name: "var_pop",
		category: "aggregate",
		description: "Population variance."
	}),
	Object.freeze({
		name: "var_samp",
		category: "aggregate",
		description: "Sample variance."
	}),
	Object.freeze({
		name: "corr",
		category: "aggregate",
		description: "Pearson correlation coefficient between two columns."
	}),
	Object.freeze({
		name: "covar_pop",
		category: "aggregate",
		description: "Population covariance between two columns."
	}),
	Object.freeze({
		name: "covar_samp",
		category: "aggregate",
		description: "Sample covariance between two columns."
	}),
	Object.freeze({
		name: "entropy",
		category: "aggregate",
		description: "Shannon entropy of the values."
	}),
	Object.freeze({
		name: "kurtosis",
		category: "aggregate",
		description: "Excess kurtosis of the values."
	}),
	Object.freeze({
		name: "skewness",
		category: "aggregate",
		description: "Skewness (third standardized moment)."
	}),
	Object.freeze({
		name: "bit_and",
		category: "aggregate",
		description: "Bitwise AND across all values."
	}),
	Object.freeze({
		name: "bit_or",
		category: "aggregate",
		description: "Bitwise OR across all values."
	}),
	Object.freeze({
		name: "bit_xor",
		category: "aggregate",
		description: "Bitwise XOR across all values."
	}),
	Object.freeze({
		name: "bool_and",
		category: "aggregate",
		description: "TRUE if every value is TRUE; ignores NULLs."
	}),
	Object.freeze({
		name: "bool_or",
		category: "aggregate",
		description: "TRUE if at least one value is TRUE."
	}),
	Object.freeze({
		name: "histogram",
		category: "aggregate",
		description: "Frequency map of values to counts."
	}),
	Object.freeze({
		name: "list",
		category: "aggregate",
		description: "Collect values into a list."
	}),
	Object.freeze({
		name: "array_agg",
		category: "aggregate",
		description: "Collect values into an array (alias for list)."
	}),
	Object.freeze({
		name: "abs",
		category: "numeric",
		description: "Absolute value."
	}),
	Object.freeze({
		name: "acos",
		category: "numeric",
		description: "Inverse cosine, in radians."
	}),
	Object.freeze({
		name: "asin",
		category: "numeric",
		description: "Inverse sine, in radians."
	}),
	Object.freeze({
		name: "atan",
		category: "numeric",
		description: "Inverse tangent, in radians."
	}),
	Object.freeze({
		name: "atan2",
		category: "numeric",
		description: "Inverse tangent of y/x with quadrant disambiguation."
	}),
	Object.freeze({
		name: "cbrt",
		category: "numeric",
		description: "Cube root."
	}),
	Object.freeze({
		name: "ceil",
		category: "numeric",
		description: "Smallest integer >= the value."
	}),
	Object.freeze({
		name: "ceiling",
		category: "numeric",
		description: "Alias for ceil."
	}),
	Object.freeze({
		name: "cos",
		category: "numeric",
		description: "Cosine; argument in radians."
	}),
	Object.freeze({
		name: "cot",
		category: "numeric",
		description: "Cotangent; argument in radians."
	}),
	Object.freeze({
		name: "degrees",
		category: "numeric",
		description: "Convert radians to degrees."
	}),
	Object.freeze({
		name: "exp",
		category: "numeric",
		description: "Exponential e^x."
	}),
	Object.freeze({
		name: "floor",
		category: "numeric",
		description: "Largest integer <= the value."
	}),
	Object.freeze({
		name: "greatest",
		category: "numeric",
		description: "Largest of the supplied non-null arguments."
	}),
	Object.freeze({
		name: "least",
		category: "numeric",
		description: "Smallest of the supplied non-null arguments."
	}),
	Object.freeze({
		name: "ln",
		category: "numeric",
		description: "Natural logarithm (base e)."
	}),
	Object.freeze({
		name: "log",
		category: "numeric",
		description: "Base-10 logarithm (alias for log10)."
	}),
	Object.freeze({
		name: "log2",
		category: "numeric",
		description: "Base-2 logarithm."
	}),
	Object.freeze({
		name: "log10",
		category: "numeric",
		description: "Base-10 logarithm."
	}),
	Object.freeze({
		name: "pi",
		category: "numeric",
		description: "Mathematical constant π."
	}),
	Object.freeze({
		name: "pow",
		category: "numeric",
		description: "x raised to the power y (alias for power)."
	}),
	Object.freeze({
		name: "power",
		category: "numeric",
		description: "x raised to the power y."
	}),
	Object.freeze({
		name: "radians",
		category: "numeric",
		description: "Convert degrees to radians."
	}),
	Object.freeze({
		name: "random",
		category: "numeric",
		description: "Pseudo-random DOUBLE in [0, 1)."
	}),
	Object.freeze({
		name: "round",
		category: "numeric",
		description: "Round to a given number of decimal places."
	}),
	Object.freeze({
		name: "sign",
		category: "numeric",
		description: "−1, 0, or 1 indicating the sign of the value."
	}),
	Object.freeze({
		name: "sin",
		category: "numeric",
		description: "Sine; argument in radians."
	}),
	Object.freeze({
		name: "sqrt",
		category: "numeric",
		description: "Square root."
	}),
	Object.freeze({
		name: "tan",
		category: "numeric",
		description: "Tangent; argument in radians."
	}),
	Object.freeze({
		name: "trunc",
		category: "numeric",
		description: "Truncate toward zero to a given decimal precision."
	}),
	Object.freeze({
		name: "factorial",
		category: "numeric",
		description: "n! (factorial of a non-negative integer)."
	}),
	Object.freeze({
		name: "even",
		category: "numeric",
		description: "TRUE when the integer is even."
	}),
	Object.freeze({
		name: "isnan",
		category: "numeric",
		description: "TRUE when the value is NaN."
	}),
	Object.freeze({
		name: "isinf",
		category: "numeric",
		description: "TRUE when the value is infinite."
	}),
	Object.freeze({
		name: "isfinite",
		category: "numeric",
		description: "TRUE when the value is finite (not NaN or ±∞)."
	}),
	Object.freeze({
		name: "ascii",
		category: "string",
		description: "Unicode codepoint of the first character."
	}),
	Object.freeze({
		name: "chr",
		category: "string",
		description: "Character corresponding to a Unicode codepoint."
	}),
	Object.freeze({
		name: "concat",
		category: "string",
		description: "Concatenate strings; NULL arguments treated as empty."
	}),
	Object.freeze({
		name: "concat_ws",
		category: "string",
		description: "Concatenate with a separator; NULLs are skipped."
	}),
	Object.freeze({
		name: "contains",
		category: "string",
		description: "TRUE when the haystack contains the needle."
	}),
	Object.freeze({
		name: "format",
		category: "string",
		description: "Python-style string formatting via {} placeholders."
	}),
	Object.freeze({
		name: "left",
		category: "string",
		description: "Leftmost N characters of the string."
	}),
	Object.freeze({
		name: "length",
		category: "string",
		description: "Number of characters in the string."
	}),
	Object.freeze({
		name: "lower",
		category: "string",
		description: "Convert to lowercase."
	}),
	Object.freeze({
		name: "lpad",
		category: "string",
		description: "Left-pad to a target length with a fill string."
	}),
	Object.freeze({
		name: "ltrim",
		category: "string",
		description: "Trim characters from the left side."
	}),
	Object.freeze({
		name: "md5",
		category: "string",
		description: "MD5 digest of the input as a hex string."
	}),
	Object.freeze({
		name: "position",
		category: "string",
		description: "1-based position of substring (0 if not found)."
	}),
	Object.freeze({
		name: "prefix",
		category: "string",
		description: "TRUE when the string starts with a prefix."
	}),
	Object.freeze({
		name: "printf",
		category: "string",
		description: "C-style printf string formatting."
	}),
	Object.freeze({
		name: "regexp_extract",
		category: "string",
		description: "Extract first regex match (or capture group)."
	}),
	Object.freeze({
		name: "regexp_full_match",
		category: "string",
		description: "TRUE when the entire string matches the regex."
	}),
	Object.freeze({
		name: "regexp_matches",
		category: "string",
		description: "TRUE when the regex matches anywhere in the string."
	}),
	Object.freeze({
		name: "regexp_replace",
		category: "string",
		description: "Replace regex matches with a replacement string."
	}),
	Object.freeze({
		name: "repeat",
		category: "string",
		description: "Repeat the string N times."
	}),
	Object.freeze({
		name: "replace",
		category: "string",
		description: "Replace all occurrences of a substring."
	}),
	Object.freeze({
		name: "reverse",
		category: "string",
		description: "Reverse the characters of the string."
	}),
	Object.freeze({
		name: "right",
		category: "string",
		description: "Rightmost N characters of the string."
	}),
	Object.freeze({
		name: "rpad",
		category: "string",
		description: "Right-pad to a target length with a fill string."
	}),
	Object.freeze({
		name: "rtrim",
		category: "string",
		description: "Trim characters from the right side."
	}),
	Object.freeze({
		name: "split_part",
		category: "string",
		description: "Nth field after splitting on a delimiter."
	}),
	Object.freeze({
		name: "starts_with",
		category: "string",
		description: "TRUE when the string starts with a prefix."
	}),
	Object.freeze({
		name: "string_split",
		category: "string",
		description: "Split a string into a list on a delimiter."
	}),
	Object.freeze({
		name: "strip_accents",
		category: "string",
		description: "Remove diacritical marks from the string."
	}),
	Object.freeze({
		name: "strlen",
		category: "string",
		description: "Number of bytes in the string (alias)."
	}),
	Object.freeze({
		name: "substr",
		category: "string",
		description: "Substring starting at a 1-based position."
	}),
	Object.freeze({
		name: "substring",
		category: "string",
		description: "Substring (alias for substr)."
	}),
	Object.freeze({
		name: "suffix",
		category: "string",
		description: "TRUE when the string ends with a suffix."
	}),
	Object.freeze({
		name: "trim",
		category: "string",
		description: "Trim characters from both sides."
	}),
	Object.freeze({
		name: "unicode",
		category: "string",
		description: "Unicode codepoint of the first character."
	}),
	Object.freeze({
		name: "upper",
		category: "string",
		description: "Convert to uppercase."
	}),
	Object.freeze({
		name: "levenshtein",
		category: "string",
		description: "Levenshtein edit distance between two strings."
	}),
	Object.freeze({
		name: "jaccard",
		category: "string",
		description: "Jaccard similarity (set overlap) of two strings."
	}),
	Object.freeze({
		name: "jaro_winkler_similarity",
		category: "string",
		description: "Jaro-Winkler similarity of two strings."
	}),
	Object.freeze({
		name: "age",
		category: "date/time",
		description: "Interval between two timestamps (or to today)."
	}),
	Object.freeze({
		name: "current_date",
		category: "date/time",
		description: "Current date in the session time zone."
	}),
	Object.freeze({
		name: "current_time",
		category: "date/time",
		description: "Current time of day."
	}),
	Object.freeze({
		name: "current_timestamp",
		category: "date/time",
		description: "Current timestamp at statement start."
	}),
	Object.freeze({
		name: "date_diff",
		category: "date/time",
		description: "Number of part boundaries crossed between two dates."
	}),
	Object.freeze({
		name: "datediff",
		category: "date/time",
		description: "Alias for date_diff."
	}),
	Object.freeze({
		name: "date_part",
		category: "date/time",
		description: "Extract a part (year, month, …) as a number."
	}),
	Object.freeze({
		name: "datepart",
		category: "date/time",
		description: "Alias for date_part."
	}),
	Object.freeze({
		name: "date_sub",
		category: "date/time",
		description: "Subtract an interval from a date/timestamp."
	}),
	Object.freeze({
		name: "date_trunc",
		category: "date/time",
		description: "Truncate a date/timestamp to a part."
	}),
	Object.freeze({
		name: "datetrunc",
		category: "date/time",
		description: "Alias for date_trunc."
	}),
	Object.freeze({
		name: "dayname",
		category: "date/time",
		description: "English day-of-week name (Monday, Tuesday, …)."
	}),
	Object.freeze({
		name: "epoch",
		category: "date/time",
		description: "Seconds since 1970-01-01 UTC."
	}),
	Object.freeze({
		name: "epoch_ms",
		category: "date/time",
		description: "Milliseconds since 1970-01-01 UTC."
	}),
	Object.freeze({
		name: "epoch_us",
		category: "date/time",
		description: "Microseconds since 1970-01-01 UTC."
	}),
	Object.freeze({
		name: "epoch_ns",
		category: "date/time",
		description: "Nanoseconds since 1970-01-01 UTC."
	}),
	Object.freeze({
		name: "extract",
		category: "date/time",
		description: "Extract a part (year, month, day, …) from a value."
	}),
	Object.freeze({
		name: "last_day",
		category: "date/time",
		description: "Last day of the month containing the input date."
	}),
	Object.freeze({
		name: "make_date",
		category: "date/time",
		description: "Build a DATE from year, month, day."
	}),
	Object.freeze({
		name: "make_time",
		category: "date/time",
		description: "Build a TIME from hour, minute, second."
	}),
	Object.freeze({
		name: "make_timestamp",
		category: "date/time",
		description: "Build a TIMESTAMP from components or microseconds."
	}),
	Object.freeze({
		name: "monthname",
		category: "date/time",
		description: "English month name (January, February, …)."
	}),
	Object.freeze({
		name: "now",
		category: "date/time",
		description: "Current timestamp at statement start."
	}),
	Object.freeze({
		name: "strftime",
		category: "date/time",
		description: "Format a date/timestamp using a strftime pattern."
	}),
	Object.freeze({
		name: "strptime",
		category: "date/time",
		description: "Parse a string using a strftime pattern."
	}),
	Object.freeze({
		name: "time_bucket",
		category: "date/time",
		description: "Bucket a timestamp into fixed-width windows."
	}),
	Object.freeze({
		name: "today",
		category: "date/time",
		description: "Current date (alias for current_date)."
	}),
	Object.freeze({
		name: "year",
		category: "date/time",
		description: "Year component of a date/timestamp."
	}),
	Object.freeze({
		name: "month",
		category: "date/time",
		description: "Month component (1-12) of a date/timestamp."
	}),
	Object.freeze({
		name: "day",
		category: "date/time",
		description: "Day-of-month component of a date/timestamp."
	}),
	Object.freeze({
		name: "hour",
		category: "date/time",
		description: "Hour component (0-23) of a time/timestamp."
	}),
	Object.freeze({
		name: "minute",
		category: "date/time",
		description: "Minute component (0-59) of a time/timestamp."
	}),
	Object.freeze({
		name: "second",
		category: "date/time",
		description: "Second component (0-59) of a time/timestamp."
	}),
	Object.freeze({
		name: "millennium",
		category: "date/time",
		description: "Millennium component of a date/timestamp."
	}),
	Object.freeze({
		name: "century",
		category: "date/time",
		description: "Century component of a date/timestamp."
	}),
	Object.freeze({
		name: "decade",
		category: "date/time",
		description: "Decade component of a date/timestamp."
	}),
	Object.freeze({
		name: "quarter",
		category: "date/time",
		description: "Quarter (1-4) of a date/timestamp."
	}),
	Object.freeze({
		name: "dayofweek",
		category: "date/time",
		description: "Day of week (0=Sunday … 6=Saturday)."
	}),
	Object.freeze({
		name: "dayofyear",
		category: "date/time",
		description: "Day of year (1-366)."
	}),
	Object.freeze({
		name: "week",
		category: "date/time",
		description: "ISO week number (1-53)."
	}),
	Object.freeze({
		name: "weekday",
		category: "date/time",
		description: "ISO weekday (1=Monday … 7=Sunday)."
	}),
	Object.freeze({
		name: "weekofyear",
		category: "date/time",
		description: "ISO week of the year (1-53)."
	}),
	Object.freeze({
		name: "yearweek",
		category: "date/time",
		description: "Year and ISO week packed as YYYYWW."
	}),
	Object.freeze({
		name: "cast",
		category: "casting",
		description: "Convert a value to a target type; errors on failure."
	}),
	Object.freeze({
		name: "try_cast",
		category: "casting",
		description: "Like CAST but returns NULL on failure."
	}),
	Object.freeze({
		name: "typeof",
		category: "casting",
		description: "Name of the value's logical type."
	}),
	Object.freeze({
		name: "coalesce",
		category: "conditional",
		description: "First non-null argument."
	}),
	Object.freeze({
		name: "ifnull",
		category: "conditional",
		description: "Replace NULL with a fallback value."
	}),
	Object.freeze({
		name: "nullif",
		category: "conditional",
		description: "NULL when the two arguments are equal."
	}),
	Object.freeze({
		name: "list_value",
		category: "list",
		description: "Construct a list from the given arguments."
	}),
	Object.freeze({
		name: "list_aggregate",
		category: "list",
		description: "Apply an aggregate function to a list."
	}),
	Object.freeze({
		name: "list_any_value",
		category: "list",
		description: "First non-null element of the list."
	}),
	Object.freeze({
		name: "list_append",
		category: "list",
		description: "Return the list with an element appended."
	}),
	Object.freeze({
		name: "list_concat",
		category: "list",
		description: "Concatenate two lists."
	}),
	Object.freeze({
		name: "list_contains",
		category: "list",
		description: "TRUE when the list contains the value."
	}),
	Object.freeze({
		name: "list_distinct",
		category: "list",
		description: "Remove duplicates from a list."
	}),
	Object.freeze({
		name: "list_filter",
		category: "list",
		description: "Keep only list elements that match a predicate."
	}),
	Object.freeze({
		name: "list_position",
		category: "list",
		description: "1-based position of the value in the list (0 if absent)."
	}),
	Object.freeze({
		name: "list_reduce",
		category: "list",
		description: "Fold the list with a binary function."
	}),
	Object.freeze({
		name: "list_reverse_sort",
		category: "list",
		description: "Sort the list in descending order."
	}),
	Object.freeze({
		name: "list_slice",
		category: "list",
		description: "Sub-list between two 1-based positions."
	}),
	Object.freeze({
		name: "list_sort",
		category: "list",
		description: "Sort the list in ascending order."
	}),
	Object.freeze({
		name: "list_transform",
		category: "list",
		description: "Map a function over each list element."
	}),
	Object.freeze({
		name: "list_unique",
		category: "list",
		description: "Number of distinct elements in the list."
	}),
	Object.freeze({
		name: "flatten",
		category: "list",
		description: "Flatten a list of lists by one level."
	}),
	Object.freeze({
		name: "generate_series",
		category: "list",
		description: "List of integers from start to end (inclusive)."
	}),
	Object.freeze({
		name: "range",
		category: "list",
		description: "List of integers from start (inclusive) to end (exclusive)."
	}),
	Object.freeze({
		name: "unnest",
		category: "list",
		description: "Expand a list into one row per element."
	}),
	Object.freeze({
		name: "array_length",
		category: "list",
		description: "Length of the array/list."
	}),
	Object.freeze({
		name: "len",
		category: "list",
		description: "Length of a list, string, or blob."
	}),
	Object.freeze({
		name: "struct_pack",
		category: "struct",
		description: "Build a STRUCT from named fields."
	}),
	Object.freeze({
		name: "struct_extract",
		category: "struct",
		description: "Extract a field from a STRUCT."
	}),
	Object.freeze({
		name: "struct_insert",
		category: "struct",
		description: "Return a STRUCT with one or more fields added."
	}),
	Object.freeze({
		name: "map",
		category: "struct",
		description: "Construct a MAP from key/value lists."
	}),
	Object.freeze({
		name: "map_from_entries",
		category: "struct",
		description: "Build a MAP from a list of key/value pairs."
	}),
	Object.freeze({
		name: "map_entries",
		category: "struct",
		description: "List of key/value pairs from a MAP."
	}),
	Object.freeze({
		name: "map_extract",
		category: "struct",
		description: "Look up a value in a MAP by key."
	}),
	Object.freeze({
		name: "map_keys",
		category: "struct",
		description: "List of keys in a MAP."
	}),
	Object.freeze({
		name: "map_values",
		category: "struct",
		description: "List of values in a MAP."
	}),
	Object.freeze({
		name: "element_at",
		category: "struct",
		description: "MAP/list lookup by key or index."
	}),
	Object.freeze({
		name: "cardinality",
		category: "struct",
		description: "Number of entries in a list, MAP, or array."
	}),
	Object.freeze({
		name: "row_number",
		category: "window",
		description: "Sequential row number within the window partition."
	}),
	Object.freeze({
		name: "rank",
		category: "window",
		description: "Rank with gaps for ties."
	}),
	Object.freeze({
		name: "dense_rank",
		category: "window",
		description: "Rank without gaps for ties."
	}),
	Object.freeze({
		name: "percent_rank",
		category: "window",
		description: "Relative rank in [0, 1]."
	}),
	Object.freeze({
		name: "cume_dist",
		category: "window",
		description: "Cumulative distribution within the partition."
	}),
	Object.freeze({
		name: "ntile",
		category: "window",
		description: "Bucket rows into N evenly-sized tiles."
	}),
	Object.freeze({
		name: "lag",
		category: "window",
		description: "Value from a row offset earlier in the partition."
	}),
	Object.freeze({
		name: "lead",
		category: "window",
		description: "Value from a row offset later in the partition."
	}),
	Object.freeze({
		name: "first_value",
		category: "window",
		description: "First value in the window frame."
	}),
	Object.freeze({
		name: "last_value",
		category: "window",
		description: "Last value in the window frame."
	}),
	Object.freeze({
		name: "nth_value",
		category: "window",
		description: "Nth value in the window frame."
	}),
	Object.freeze({
		name: "hash",
		category: "utility",
		description: "64-bit hash of the input value."
	}),
	Object.freeze({
		name: "sha256",
		category: "utility",
		description: "SHA-256 digest of the input as a hex string."
	}),
	Object.freeze({
		name: "uuid",
		category: "utility",
		description: "Random UUID v4."
	}),
	Object.freeze({
		name: "gen_random_uuid",
		category: "utility",
		description: "Random UUID v4 (alias for uuid())."
	}),
	Object.freeze({
		name: "version",
		category: "utility",
		description: "DuckDB version string."
	})
]), h = o.theme({
	"&": { fontSize: "13px" },
	".cm-content": {
		fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace",
		padding: "0.5rem",
		caretColor: "var(--dt-text)"
	},
	"&.cm-focused": { outline: "none" },
	".cm-activeLine": { backgroundColor: "var(--dt-bg-secondary)" },
	".cm-selectionBackground": { backgroundColor: "var(--dt-primary-lighter) !important" },
	".cm-cursor": { borderLeftColor: "var(--dt-text)" },
	".cm-gutters": { display: "none" },
	".cm-scroller": { overflow: "auto" }
}), g = f(d.define([
	{
		tag: p.keyword,
		color: "var(--dt-primary)",
		fontWeight: "bold"
	},
	{
		tag: p.string,
		color: "var(--dt-syntax-string)"
	},
	{
		tag: p.number,
		color: "var(--dt-primary)"
	},
	{
		tag: p.comment,
		color: "var(--dt-text-tertiary)",
		fontStyle: "italic"
	},
	{
		tag: p.function(p.variableName),
		fontWeight: "bold"
	},
	{
		tag: p.operator,
		color: "var(--dt-text-secondary)"
	},
	{
		tag: p.typeName,
		color: "var(--dt-syntax-type)"
	},
	{
		tag: p.null,
		color: "var(--dt-text-tertiary)"
	},
	{
		tag: p.bool,
		color: "var(--dt-primary)"
	}
]));
//#endregion
//#region src/sql-editor/extensions.ts
function _(e, t = {}) {
	let n = { columns: e.map((e) => ({
		name: e.name,
		type: e.originalType ?? e.type ?? "",
		isDerived: e.isDerived === !0
	})) };
	return t.functions !== void 0 && (n.functions = [...t.functions]), n;
}
function v(e, t = {}) {
	let n = t.includeTheme !== !1, r = t.upperCaseKeywords !== !1, i = t.functions ?? e.functions ?? m, a = e.columns.map((e) => ({
		label: e.name,
		type: "variable",
		detail: e.type,
		boost: 0
	})), o = y(i), s = [...a, ...o], c = [u({
		dialect: l,
		upperCaseKeywords: r
	}), l.language.data.of({ autocomplete: (e) => {
		let t = e.matchBefore(/\w+/);
		return !t && !e.explicit ? null : {
			from: t?.from ?? e.pos,
			options: s,
			validFor: /^\w*$/
		};
	} })];
	return n && c.push(h, g), c;
}
function y(e) {
	return e.length === 0 ? [] : typeof e[0] == "string" ? e.map((e) => ({
		label: e,
		type: "function",
		boost: -1
	})) : e.map((e) => ({
		label: e.name,
		type: "function",
		detail: e.category,
		info: e.description,
		boost: -1
	}));
}
//#endregion
//#region src/sql-editor/CodeMirrorExpressionEditor.ts
var b = class {
	element;
	view;
	errorDiv;
	sqlCompartment;
	prefix;
	constructor(l, u, d = "dt", f) {
		this.prefix = d, this.sqlCompartment = new i(), this.element = document.createElement("div"), this.element.className = `${this.prefix}-cm-expr-editor`;
		let p = a.create({
			doc: "",
			extensions: [
				this.sqlCompartment.of(this.buildCompletionExtensions(u)),
				e({ tooltipClass: () => `${this.prefix}-cm-autocomplete` }),
				s.of([...t, ...r]),
				n(),
				h,
				g,
				c(f?.placeholder ?? "Enter SQL expression, e.g. price * quantity"),
				o.theme({ "&": {
					minHeight: "80px",
					maxHeight: "200px"
				} }),
				o.updateListener.of((e) => {
					e.docChanged && this.element.dispatchEvent(new Event("input", { bubbles: !0 }));
				}),
				o.contentAttributes.of({ "aria-label": "SQL Expression" })
			]
		});
		this.view = new o({
			state: p,
			parent: this.element
		}), this.errorDiv = document.createElement("div"), this.errorDiv.className = `${this.prefix}-expr-editor-error`, this.errorDiv.style.display = "none", this.element.appendChild(this.errorDiv), l.appendChild(this.element);
	}
	getValue() {
		return this.view.state.doc.toString();
	}
	setValue(e) {
		this.view.dispatch({ changes: {
			from: 0,
			to: this.view.state.doc.length,
			insert: e
		} });
	}
	focus() {
		this.view.focus();
	}
	setError(e) {
		e === null ? (this.element.classList.remove(`${this.prefix}-cm-expr-editor--error`), this.errorDiv.textContent = "", this.errorDiv.style.display = "none") : (this.element.classList.add(`${this.prefix}-cm-expr-editor--error`), this.errorDiv.textContent = e, this.errorDiv.style.display = "");
	}
	updateCompletionContext(e) {
		this.view.dispatch({ effects: this.sqlCompartment.reconfigure(this.buildCompletionExtensions(e)) });
	}
	destroy() {
		this.view.destroy(), this.element.parentNode && this.element.parentNode.removeChild(this.element);
	}
	buildCompletionExtensions(e) {
		return v(e, { includeTheme: !1 });
	}
};
//#endregion
export { h as a, g as i, _ as n, m as o, v as r, b as t };

//# sourceMappingURL=CodeMirrorExpressionEditor-BOO5Hr5e.js.map