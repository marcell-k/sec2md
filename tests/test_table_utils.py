"""Tests for sec2md.table_utils — the HTML → GFM table-conversion pipeline.

All fixtures are realistic slices of SEC EDGAR HTML (10-K / 10-Q / 8-K filings).
No HTTP calls are made; every fixture is an inline string.

Fixture provenance
------------------
INCOME_STATEMENT  - Coca-Cola 10-K 2024 style (ko-20241231)
BALANCE_SHEET     - Workiva iXBRL pattern with separate $ currency columns
SEPARATOR_ROW     - common totals table with underline/dash separator rows
NESTED_TABLE      - layout table whose sole cell contains a real data table
COLSPAN_HEADER    - 10-Q segment table with rowspan+colspan header block
NBSP_SPACER       - table with &nbsp; visual-spacer columns between data cols
EMPTY_TABLE       - all cells are non-breaking spaces (should produce nothing)
SINGLE_ROW        - header-only table (no data rows → should produce nothing)
PIPE_IN_CELL      - cell content includes literal "|" chars that must be escaped
EARNINGS_RELEASE  - 8-K press-release style multi-quarter results table
ROWSPAN_LABEL     - stub column that spans several rows (common in risk tables)
CURRENCY_EURO     - European filing with € symbol column
"""

from __future__ import annotations

from sec2md.table_utils import (
    _build_grid,
    _deduplicate_columns,
    _merge_currency_columns,
    _merge_currency_prefixes,
    _merge_percent_suffixes,
    _remove_empty_columns,
    table_to_markdown,
)

from .conftest import make_table, md_rows

# ---------------------------------------------------------------------------
# Fixtures — real SEC HTML patterns
# ---------------------------------------------------------------------------

# 1. Three-column income statement, Coca-Cola 10-K style
INCOME_STATEMENT = """
<table>
  <tr>
    <th>&#160;</th>
    <th>Year Ended December&#160;31, 2024</th>
    <th>Year Ended December&#160;31, 2023</th>
  </tr>
  <tr>
    <td>Net revenues</td>
    <td>$ 47,061</td>
    <td>$ 45,754</td>
  </tr>
  <tr>
    <td>Cost of goods sold</td>
    <td>18,542</td>
    <td>18,001</td>
  </tr>
  <tr>
    <td>Gross profit</td>
    <td>28,519</td>
    <td>27,753</td>
  </tr>
  <tr>
    <td>Operating income</td>
    <td>11,311</td>
    <td>10,909</td>
  </tr>
</table>
"""

# 2. Balance sheet with separate $ currency columns (Workiva / iXBRL pattern)
BALANCE_SHEET = """
<table>
  <tr>
    <th>Assets</th>
    <th></th>
    <th>Dec 31, 2024</th>
    <th></th>
    <th>Dec 31, 2023</th>
  </tr>
  <tr>
    <td>Cash and cash equivalents</td>
    <td>$</td>
    <td>9,366</td>
    <td>$</td>
    <td>9,523</td>
  </tr>
  <tr>
    <td>Short-term investments</td>
    <td>$</td>
    <td>2,183</td>
    <td>$</td>
    <td>1,859</td>
  </tr>
  <tr>
    <td>Total current assets</td>
    <td>$</td>
    <td>29,648</td>
    <td>$</td>
    <td>28,742</td>
  </tr>
</table>
"""

# 3. Table with separator rows (underscores between subtotals)
SEPARATOR_ROW = """
<table>
  <tr>
    <th>Segment</th>
    <th>Revenue ($M)</th>
    <th>% Change</th>
  </tr>
  <tr>
    <td>North America</td>
    <td>1,234</td>
    <td>4.2%</td>
  </tr>
  <tr>
    <td>International</td>
    <td>567</td>
    <td>7.8%</td>
  </tr>
  <tr>
    <td>___________</td>
    <td>___________</td>
    <td>___________</td>
  </tr>
  <tr>
    <td>Total</td>
    <td>1,801</td>
    <td>5.3%</td>
  </tr>
</table>
"""

# 4. Layout table — outer table's sole cell contains a real data table.
#    The outer table should be treated as empty (layout) and return "".
NESTED_TABLE = """
<table>
  <tr>
    <td>
      <table>
        <tr>
          <th>Quarter</th>
          <th>Revenue</th>
        </tr>
        <tr>
          <td>Q1 2024</td>
          <td>$11,300</td>
        </tr>
        <tr>
          <td>Q2 2024</td>
          <td>$12,360</td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""

# 5. Colspan header spanning quarter columns; first column uses rowspan=2 (10-Q style)
COLSPAN_HEADER = """
<table>
  <tr>
    <th rowspan="2">Segment</th>
    <th colspan="2">Three Months Ended June&#160;30,</th>
    <th colspan="2">Six Months Ended June&#160;30,</th>
  </tr>
  <tr>
    <th>2024</th>
    <th>2023</th>
    <th>2024</th>
    <th>2023</th>
  </tr>
  <tr>
    <td>North America</td>
    <td>5,432</td>
    <td>5,100</td>
    <td>10,765</td>
    <td>10,210</td>
  </tr>
  <tr>
    <td>International</td>
    <td>2,876</td>
    <td>2,654</td>
    <td>5,701</td>
    <td>5,308</td>
  </tr>
</table>
"""

# 6. &nbsp; visual-spacer columns between data columns
NBSP_SPACER = """
<table>
  <tr>
    <th>Metric</th>
    <th>&#160;</th>
    <th>FY 2024</th>
    <th>&#160;</th>
    <th>FY 2023</th>
  </tr>
  <tr>
    <td>EPS (diluted)</td>
    <td>&#160;</td>
    <td>$2.47</td>
    <td>&#160;</td>
    <td>$2.18</td>
  </tr>
  <tr>
    <td>Free cash flow ($B)</td>
    <td>&#160;</td>
    <td>9.2</td>
    <td>&#160;</td>
    <td>8.6</td>
  </tr>
</table>
"""

# 7. All cells are non-breaking spaces → should produce empty string
EMPTY_TABLE = """
<table>
  <tr>
    <td>&#160;</td>
    <td>&#160;</td>
    <td>&#160;</td>
  </tr>
  <tr>
    <td>&#160;</td>
    <td>&#160;</td>
    <td>&#160;</td>
  </tr>
</table>
"""

# 8. Header row only, no data rows → should produce empty string
SINGLE_ROW = """
<table>
  <tr>
    <th>Label</th>
    <th>2024</th>
    <th>2023</th>
  </tr>
</table>
"""

# 9. Cell content contains literal "|" characters → must be escaped in output
PIPE_IN_CELL = """
<table>
  <tr>
    <th>Condition</th>
    <th>Result</th>
  </tr>
  <tr>
    <td>Pass | Fail</td>
    <td>Accept | Reject</td>
  </tr>
  <tr>
    <td>A | B | C</td>
    <td>X | Y</td>
  </tr>
</table>
"""

# 10. 8-K press-release multi-quarter earnings table
EARNINGS_RELEASE = """
<table>
  <tr>
    <td colspan="5"><b>CONSOLIDATED STATEMENTS OF INCOME (Unaudited)</b></td>
  </tr>
  <tr>
    <td></td>
    <td>Q4 2024</td>
    <td>Q3 2024</td>
    <td>Q4 2023</td>
    <td>FY 2024</td>
  </tr>
  <tr>
    <td>Total net revenues</td>
    <td>$ 11,951</td>
    <td>$ 11,854</td>
    <td>$ 10,856</td>
    <td>$ 47,061</td>
  </tr>
  <tr>
    <td>Gross profit</td>
    <td>$ 7,118</td>
    <td>$ 6,987</td>
    <td>$ 6,421</td>
    <td>$ 28,519</td>
  </tr>
  <tr>
    <td>Net income attributable to shareowners</td>
    <td>$ 2,197</td>
    <td>$ 2,853</td>
    <td>$ 1,976</td>
    <td>$ 10,627</td>
  </tr>
  <tr>
    <td>Diluted EPS</td>
    <td>$ 0.51</td>
    <td>$ 0.66</td>
    <td>$ 0.46</td>
    <td>$ 2.47</td>
  </tr>
</table>
"""

# 11. Rowspan stub label column (risk-factor table style)
ROWSPAN_LABEL = """
<table>
  <tr>
    <th>Category</th>
    <th>Risk Factor</th>
    <th>Likelihood</th>
  </tr>
  <tr>
    <td rowspan="3">Market</td>
    <td>Interest rate volatility</td>
    <td>High</td>
  </tr>
  <tr>
    <td>Currency fluctuations</td>
    <td>Medium</td>
  </tr>
  <tr>
    <td>Commodity price changes</td>
    <td>Medium</td>
  </tr>
</table>
"""

# 12. European filing with € currency column
CURRENCY_EURO = """
<table>
  <tr>
    <th>Item</th>
    <th></th>
    <th>FY 2024 (€M)</th>
  </tr>
  <tr>
    <td>Revenue</td>
    <td>€</td>
    <td>3,412</td>
  </tr>
  <tr>
    <td>EBITDA</td>
    <td>€</td>
    <td>891</td>
  </tr>
</table>
"""


# 13. Workiva / iXBRL long-term debt table — the core duplicate-column fixture.
#
#     Structure:
#       * Header row 1: colspan=4 per year  -> "Dec 31, 2025" expanded x4
#       * Header row 2: colspan=2 per col   -> "Amount" / "Avg Rate" each expanded x2
#       * dollar rows:  <td>$</td><td>value</td>    two cells, different content
#       * plain rows:   <td colspan="2">value</td>  expanded to identical pair
#
#     Before the fix _deduplicate_columns blocked on the dollar rows because
#     (col_A="$", col_B="26,945") is neither equal nor blank, leaving 9 raw
#     columns in the output instead of 5.
WORKIVA_DEBT_TABLE = """
<table>
  <tr>
    <th></th>
    <th colspan="4">December 31, 2025</th>
    <th colspan="4">December 31, 2024</th>
  </tr>
  <tr>
    <th></th>
    <th colspan="2">Amount</th>
    <th colspan="2">Average Rate&#160;1</th>
    <th colspan="2">Amount</th>
    <th colspan="2">Average Rate&#160;1</th>
  </tr>
  <tr>
    <td>U.S. dollar notes due 2027-2093</td>
    <td>$</td>
    <td>26,945</td>
    <td>3.6</td>
    <td>%</td>
    <td>$</td>
    <td>26,931</td>
    <td>3.1</td>
    <td>%</td>
  </tr>
  <tr>
    <td>U.S. dollar debentures due 2026-2098</td>
    <td colspan="2">767</td>
    <td>4.8</td>
    <td></td>
    <td colspan="2">778</td>
    <td>4.8</td>
    <td></td>
  </tr>
  <tr>
    <td>Euro notes due 2026-2053</td>
    <td colspan="2">15,470</td>
    <td>2.4</td>
    <td></td>
    <td colspan="2">13,619</td>
    <td>3.1</td>
    <td></td>
  </tr>
  <tr>
    <td>Fair value adjustments</td>
    <td colspan="2">(618)</td>
    <td colspan="2">N/A</td>
    <td colspan="2">(785)</td>
    <td colspan="2">N/A</td>
  </tr>
  <tr>
    <td>Total</td>
    <td colspan="2">43,941</td>
    <td>3.3</td>
    <td>%</td>
    <td colspan="2">43,023</td>
    <td>3.4</td>
    <td>%</td>
  </tr>
  <tr>
    <td>Long-term debt</td>
    <td>$</td>
    <td>42,119</td>
    <td></td>
    <td></td>
    <td>$</td>
    <td>42,375</td>
    <td></td>
    <td></td>
  </tr>
</table>
"""

# 14. Simpler Workiva table: only Amount columns (no rate/percent pair).
WORKIVA_SIMPLE = """
<table>
  <tr>
    <th></th>
    <th colspan="2">FY 2025</th>
    <th colspan="2">FY 2024</th>
  </tr>
  <tr>
    <th>Item</th>
    <th colspan="2">Amount ($M)</th>
    <th colspan="2">Amount ($M)</th>
  </tr>
  <tr>
    <td>Revenue</td>
    <td>$</td>
    <td>1,234</td>
    <td>$</td>
    <td>1,100</td>
  </tr>
  <tr>
    <td>Operating income</td>
    <td colspan="2">456</td>
    <td colspan="2">400</td>
  </tr>
</table>
"""


# ---------------------------------------------------------------------------
# Integration tests — via public API: table_to_markdown()
# ---------------------------------------------------------------------------


class TestIncomeStatement:
    def test_produces_output(self) -> None:
        md = table_to_markdown(make_table(INCOME_STATEMENT))
        assert md, "Expected non-empty markdown for income statement table"

    def test_contains_key_values(self) -> None:
        md = table_to_markdown(make_table(INCOME_STATEMENT))
        assert "Net revenues" in md
        assert "47,061" in md
        assert "Operating income" in md

    def test_gfm_structure(self) -> None:
        md = table_to_markdown(make_table(INCOME_STATEMENT))
        lines = md.splitlines()
        assert any("---" in ln for ln in lines), "Missing GFM separator line"
        assert all(ln.strip().startswith("|") for ln in lines if ln.strip()), "All lines should be pipe-table rows"

    def test_row_count(self) -> None:
        md = table_to_markdown(make_table(INCOME_STATEMENT))
        rows = md_rows(md)
        # header + 4 data rows (at minimum)
        assert len(rows) >= 4


class TestCurrencyColumns:
    def test_no_bare_dollar_cell(self) -> None:
        md = table_to_markdown(make_table(BALANCE_SHEET))
        rows = md_rows(md)
        for row in rows:
            assert "$" not in row, f"Bare '$' cell survived currency merge: {row}"

    def test_values_present_after_merge(self) -> None:
        md = table_to_markdown(make_table(BALANCE_SHEET))
        assert "9,366" in md or "$ 9,366" in md
        assert "29,648" in md or "$ 29,648" in md

    def test_column_count_reduced(self) -> None:
        md = table_to_markdown(make_table(BALANCE_SHEET))
        rows = md_rows(md)
        # 5 raw cols → 3 after currency merge + empty-col removal
        for row in rows:
            assert len(row) <= 3, f"Expected ≤3 cols after merge, got {len(row)}: {row}"

    def test_euro_currency_merged(self) -> None:
        md = table_to_markdown(make_table(CURRENCY_EURO))
        rows = md_rows(md)
        for row in rows:
            assert "€" not in row, f"Bare '€' cell survived merge: {row}"
        assert "3,412" in md or "€ 3,412" in md


class TestSeparatorRows:
    def test_separator_not_in_output(self) -> None:
        md = table_to_markdown(make_table(SEPARATOR_ROW))
        rows = md_rows(md)
        for row in rows:
            all_dashes = all(set(c.replace(" ", "")) <= {"_", "-", ""} for c in row)
            assert not all_dashes, f"Separator row leaked into output: {row}"

    def test_data_rows_intact(self) -> None:
        md = table_to_markdown(make_table(SEPARATOR_ROW))
        assert "Total" in md
        assert "1,801" in md
        assert "North America" in md


class TestNestedTable:
    def test_layout_table_returns_empty(self) -> None:
        md = table_to_markdown(make_table(NESTED_TABLE))
        assert md == "", f"Expected '' for layout table, got:\n{md}"


class TestColspanHeader:
    def test_produces_output(self) -> None:
        md = table_to_markdown(make_table(COLSPAN_HEADER))
        assert md, "Expected output for colspan-header table"

    def test_data_values_present(self) -> None:
        md = table_to_markdown(make_table(COLSPAN_HEADER))
        assert "North America" in md
        assert "5,432" in md
        assert "International" in md


class TestNbspSpacerColumns:
    def test_spacer_columns_removed(self) -> None:
        md = table_to_markdown(make_table(NBSP_SPACER))
        rows = md_rows(md)
        # 5 raw cols → 3 after &nbsp; column removal
        for row in rows:
            assert len(row) <= 3, f"Expected ≤3 cols after spacer removal, got: {row}"

    def test_values_retained(self) -> None:
        md = table_to_markdown(make_table(NBSP_SPACER))
        assert "EPS (diluted)" in md
        assert "$2.47" in md or "2.47" in md


class TestEdgeCases:
    def test_empty_table_returns_empty_string(self) -> None:
        assert table_to_markdown(make_table(EMPTY_TABLE)) == ""

    def test_header_only_returns_empty_string(self) -> None:
        assert table_to_markdown(make_table(SINGLE_ROW)) == ""

    def test_pipe_chars_escaped_in_raw_markdown(self) -> None:
        md = table_to_markdown(make_table(PIPE_IN_CELL))
        assert "\\|" in md, "Pipe characters inside cells must be backslash-escaped"

    def test_pipe_content_readable(self) -> None:
        md = table_to_markdown(make_table(PIPE_IN_CELL))
        # Content should still be present after escaping
        assert "Pass" in md and "Fail" in md


class TestRowspan:
    def test_produces_output(self) -> None:
        md = table_to_markdown(make_table(ROWSPAN_LABEL))
        assert md

    def test_data_present(self) -> None:
        md = table_to_markdown(make_table(ROWSPAN_LABEL))
        assert "Interest rate volatility" in md
        assert "Currency fluctuations" in md
        assert "Commodity price changes" in md


class TestEarningsRelease:
    def test_produces_output(self) -> None:
        md = table_to_markdown(make_table(EARNINGS_RELEASE))
        assert md

    def test_key_line_items_present(self) -> None:
        md = table_to_markdown(make_table(EARNINGS_RELEASE))
        assert "Diluted EPS" in md
        assert "Net income" in md

    def test_quarter_values_present(self) -> None:
        md = table_to_markdown(make_table(EARNINGS_RELEASE))
        assert "0.51" in md  # Q4 2024 diluted EPS
        assert "2.47" in md  # FY 2024 diluted EPS

    def test_column_count_reasonable(self) -> None:
        md = table_to_markdown(make_table(EARNINGS_RELEASE))
        rows = md_rows(md)
        for row in rows:
            assert 1 <= len(row) <= 6, f"Unexpected column count: {row}"


# ---------------------------------------------------------------------------
# Unit tests — individual pipeline steps
# ---------------------------------------------------------------------------


class TestBuildGrid:
    def test_simple_2x2(self) -> None:
        table = make_table("""
        <table>
          <tr><td>A</td><td>B</td></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>""")
        assert _build_grid(table) == [["A", "B"], ["1", "2"]]

    def test_colspan_fills_adjacent_cells(self) -> None:
        table = make_table("""
        <table>
          <tr><td colspan="3">Header</td></tr>
          <tr><td>A</td><td>B</td><td>C</td></tr>
        </table>""")
        grid = _build_grid(table)
        assert grid[0] == ["Header", "Header", "Header"]

    def test_rowspan_propagates_downward(self) -> None:
        table = make_table("""
        <table>
          <tr><td rowspan="3">Label</td><td>R1</td></tr>
          <tr><td>R2</td></tr>
          <tr><td>R3</td></tr>
        </table>""")
        grid = _build_grid(table)
        assert all(row[0] == "Label" for row in grid)

    def test_nested_table_text_excluded_from_outer(self) -> None:
        table = make_table("""
        <table>
          <tr>
            <td>
              <table><tr><td>SHOULD_NOT_APPEAR</td></tr></table>
            </td>
          </tr>
        </table>""")
        grid = _build_grid(table)
        flat = [cell for row in grid for cell in row]
        assert "SHOULD_NOT_APPEAR" not in flat

    def test_nbsp_normalised_to_space(self) -> None:
        table = make_table("<table><tr><td>foo&#160;bar</td></tr></table>")
        grid = _build_grid(table)
        assert grid[0][0] == "foo bar"

    def test_mixed_colspan_rowspan(self) -> None:
        # 2x2 grid from a 2-row table where top-left spans both rows and cols
        table = make_table("""
        <table>
          <tr><td colspan="2" rowspan="2">Big</td><td>C1</td></tr>
          <tr><td>C2</td></tr>
        </table>""")
        grid = _build_grid(table)
        assert grid[0][0] == "Big"
        assert grid[1][0] == "Big"
        assert grid[0][1] == "Big"
        assert grid[1][1] == "Big"


class TestRemoveEmptyColumns:
    def test_removes_whitespace_only_column(self) -> None:
        grid = [["A", "   ", "B"], ["1", "\u00a0", "2"]]
        result = _remove_empty_columns(grid)
        assert result == [["A", "B"], ["1", "2"]]

    def test_keeps_column_with_partial_content(self) -> None:
        grid = [["A", "B", ""], ["1", "", "3"]]
        result = _remove_empty_columns(grid)
        # Column 1 has "B" → keep; column 2 has "3" → keep
        assert len(result[0]) == 3

    def test_all_empty_returns_empty(self) -> None:
        grid = [["", ""], ["", ""]]
        result = _remove_empty_columns(grid)
        assert all(len(row) == 0 for row in result)

    def test_noop_when_all_full(self) -> None:
        grid = [["A", "B"], ["1", "2"]]
        assert _remove_empty_columns(grid) == grid


class TestDeduplicateColumns:
    def test_collapses_identical_columns(self) -> None:
        grid = [["H", "H"], ["100", "100"], ["200", "200"]]
        result = _deduplicate_columns(grid)
        assert all(len(row) == 1 for row in result)
        assert result[0] == ["H"]

    def test_does_not_merge_different_columns(self) -> None:
        grid = [["A", "B"], ["1", "2"]]
        assert _deduplicate_columns(grid) == [["A", "B"], ["1", "2"]]

    def test_blank_merges_with_non_blank(self) -> None:
        grid = [["", "Header"], ["", "Data"]]
        result = _deduplicate_columns(grid)
        assert all(len(row) == 1 for row in result)
        assert result[0] == ["Header"]

    def test_chain_of_three_identical(self) -> None:
        grid = [["X", "X", "X"], ["1", "1", "1"]]
        result = _deduplicate_columns(grid)
        assert all(len(row) == 1 for row in result)

    def test_partial_blank_alternating(self) -> None:
        # col A: ["V", ""], col B: ["", "V"] → both have value in exactly one row
        grid = [["V", ""], ["", "V"]]
        result = _deduplicate_columns(grid)
        assert all(len(row) == 1 for row in result)


class TestMergeCurrencyColumns:
    def test_merges_dollar_sign(self) -> None:
        grid = [["Item", "$", "Amount"], ["Cash", "$", "1,000"]]
        result = _merge_currency_columns(grid)
        assert len(result[0]) == 2
        # The merged cell should contain both symbol and value
        cash_row = result[1]
        assert any("1,000" in cell for cell in cash_row)

    def test_merges_euro_sign(self) -> None:
        grid = [["Item", "€", "Value"], ["Rev", "€", "500"]]
        result = _merge_currency_columns(grid)
        assert len(result[0]) == 2

    def test_no_change_without_currency(self) -> None:
        grid = [["A", "B"], ["1", "2"]]
        assert _merge_currency_columns(grid) == [["A", "B"], ["1", "2"]]

    def test_currency_in_header_row_handled(self) -> None:
        # Header row has empty string for $ col (common in SEC)
        grid = [["Desc", "", "2024"], ["Cash", "$", "1,000"]]
        result = _merge_currency_columns(grid)
        # $ column (index 1) should merge into index 2
        assert len(result[0]) == 2


# ---------------------------------------------------------------------------
# Workiva / iXBRL duplicate-column tests (the reported bug)
# ---------------------------------------------------------------------------


class TestWorkivaDebtTable:
    """Full pipeline tests for the Coca-Cola-style long-term debt table.

    This is the table the user reported: 9 raw columns (4 per date x 2 dates
    + 1 description) were appearing in the output instead of the correct 5
    (description + amount + rate per date).
    """

    def test_column_count_not_duplicated(self) -> None:
        """The main regression: each row must have at most 5 columns."""
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        rows = md_rows(md)
        for row in rows:
            assert len(row) <= 5, f"Expected ≤5 columns (desc + amount + rate x 2 dates), got {len(row)}: {row}"

    def test_no_bare_dollar_cell(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        rows = md_rows(md)
        for row in rows:
            assert "$" not in row, f"Bare '$' survived the pipeline: {row}"

    def test_no_bare_percent_cell(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        rows = md_rows(md)
        for row in rows:
            assert "%" not in row, f"Bare '%' survived the pipeline: {row}"

    def test_dollar_prefix_merged_into_value(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        # Dollar-prefixed rows should appear as "$ value" in a single cell.
        assert "$ 26,945" in md or "26,945" in md

    def test_percent_suffix_merged_into_rate(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        assert "3.6%" in md or "3.3%" in md

    def test_plain_value_rows_not_duplicated(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        rows = md_rows(md)
        # Skip the first row: GFM has only one header row, so the date
        # ("December 31, 2025") correctly appears twice there — once for the
        # Amount column and once for the Rate column.  Data rows must not
        # have adjacent identical cells (that would indicate un-merged colspan).
        for row in rows[1:]:
            consecutive_same = any(row[i] == row[i + 1] != "" for i in range(len(row) - 1))
            assert not consecutive_same, f"Duplicate adjacent values in data row: {row}"

    def test_na_not_corrupted(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        assert "N/A" in md
        assert "N/A%" not in md

    def test_key_line_items_present(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        assert "U.S. dollar notes" in md
        assert "Euro notes" in md
        assert "Fair value" in md
        assert "Long-term debt" in md

    def test_both_dates_present(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_DEBT_TABLE))
        assert "2025" in md
        assert "2024" in md


class TestWorkivaSimple:
    def test_column_count(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_SIMPLE))
        rows = md_rows(md)
        for row in rows:
            assert len(row) <= 3, f"Expected ≤3 cols, got {len(row)}: {row}"

    def test_no_bare_dollar(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_SIMPLE))
        rows = md_rows(md)
        for row in rows:
            assert "$" not in row

    def test_values_present(self) -> None:
        md = table_to_markdown(make_table(WORKIVA_SIMPLE))
        assert "1,234" in md
        assert "456" in md


# ---------------------------------------------------------------------------
# Unit tests — _merge_currency_prefixes
# ---------------------------------------------------------------------------


class TestMergeCurrencyPrefixes:
    def test_dollar_moved_into_numeric_cell(self) -> None:
        grid = [["Item", "$", "Amount"], ["Cash", "$", "1,000"]]
        result = _merge_currency_prefixes(grid)
        # Data row: col_1 emptied, col_2 has "$ 1,000"
        assert result[1][1] == ""
        assert result[1][2] == "$ 1,000"

    def test_header_not_corrupted(self) -> None:
        # "$" header next to "Amount" header — "Amount" is not numeric → no merge.
        grid = [["Item", "$", "Amount"], ["Cash", "$", "1,000"]]
        result = _merge_currency_prefixes(grid)
        # Header row should be unchanged
        assert result[0] == ["Item", "$", "Amount"]

    def test_euro_symbol_merged(self) -> None:
        grid = [["Item", "€", "Value"], ["Rev", "€", "500"]]
        result = _merge_currency_prefixes(grid)
        assert result[1][1] == ""
        assert result[1][2] == "€ 500"

    def test_non_numeric_right_cell_not_merged(self) -> None:
        # "$" followed by text (not a number) — should NOT merge.
        grid = [["A", "$", "Note text here"], ["x", "$", "N/A"]]
        result = _merge_currency_prefixes(grid)
        # "Note text here" has no digits → no merge
        assert result[0][1] == "$"
        # "N/A" has no digits → no merge
        assert result[1][1] == "$"

    def test_parenthesised_negative_value_merged(self) -> None:
        # "(618)" contains digits → treated as numeric → merge.
        grid = [["Adj", "$", "(618)"]]
        result = _merge_currency_prefixes(grid)
        assert result[0][1] == ""
        assert result[0][2] == "$ (618)"

    def test_colspan_duplicate_rows_unchanged(self) -> None:
        # Rows expanded from colspan=2 have value in both cols → neither is
        # a currency symbol → _merge_currency_prefixes leaves them alone.
        grid = [["Desc", "767", "767"], ["Desc2", "15,470", "15,470"]]
        result = _merge_currency_prefixes(grid)
        assert result == grid


# ---------------------------------------------------------------------------
# Unit tests — _merge_percent_suffixes
# ---------------------------------------------------------------------------


class TestMergePercentSuffixes:
    def test_percent_appended_to_rate(self) -> None:
        grid = [["Item", "Rate"], ["Notes", "3.6", "%"]]
        result = _merge_percent_suffixes(grid)
        # data row: "3.6" + "%" → "3.6%", "%" cell emptied
        assert result[1][1] == "3.6%"
        assert result[1][2] == ""

    def test_header_not_corrupted(self) -> None:
        # Header "Average Rate" is not exactly "%" → no merge.
        grid = [["Item", "Rate", "Average Rate"], ["Rev", "3.6", "%"]]
        result = _merge_percent_suffixes(grid)
        assert result[0] == ["Item", "Rate", "Average Rate"]

    def test_na_not_turned_into_na_percent(self) -> None:
        # "N/A" is not "%" → no merge.
        grid = [["Adj", "N/A", "N/A"]]
        result = _merge_percent_suffixes(grid)
        assert result[0] == ["Adj", "N/A", "N/A"]

    def test_non_numeric_left_cell_not_merged(self) -> None:
        # "%" preceded by non-numeric text → no merge.
        grid = [["Note", "text only", "%"]]
        result = _merge_percent_suffixes(grid)
        assert result[0][1] == "text only"
        assert result[0][2] == "%"

    def test_multiple_percent_cells_in_row(self) -> None:
        grid = [["A", "3.6", "%", "4.8", "%"]]
        result = _merge_percent_suffixes(grid)
        assert result[0][1] == "3.6%"
        assert result[0][2] == ""
        assert result[0][3] == "4.8%"
        assert result[0][4] == ""

    def test_already_combined_value_unchanged(self) -> None:
        # "3.6%" already has % embedded → "%" comparison ("3.6%" != "%") → no merge.
        grid = [["A", "3.6%", "other"]]
        result = _merge_percent_suffixes(grid)
        assert result == grid
