function isRangeMatchQuoteChar(char) {
  return char === "'" || char === '"' || char === "\u2018" || char === "\u2019" || char === "\u201c" || char === "\u201d";
}

function buildCanonicalTextIndexMap(text) {
  let normalized = "";
  const spans = [];
  const chars = Array.from(String(text ?? ""));
  let inSingleQuote = false;
  let inDoubleQuote = false;
  let inLineComment = false;
  let inBlockComment = false;

  for (let index = 0; index < chars.length; index += 1) {
    const char = chars[index];
    const nextChar = chars[index + 1];

    if (inLineComment) {
      if (char === "\n" || char === "\r") inLineComment = false;
      continue;
    }

    if (inBlockComment) {
      if (char === "*" && nextChar === "/") {
        index += 1;
        inBlockComment = false;
      }
      continue;
    }

    if (!inSingleQuote && !inDoubleQuote && char === "-" && nextChar === "-") {
      inLineComment = true;
      index += 1;
      continue;
    }

    if (!inSingleQuote && !inDoubleQuote && char === "/" && nextChar === "*") {
      inBlockComment = true;
      index += 1;
      continue;
    }

    if (char === "'" && !inDoubleQuote) {
      if (inSingleQuote && nextChar === "'") {
        normalized += "'";
        spans.push({ start: index, end: index + 2 });
        index += 1;
        continue;
      }
      inSingleQuote = !inSingleQuote;
      normalized += "'";
      spans.push({ start: index, end: index + 1 });
      continue;
    }

    if (char === '"' && !inSingleQuote) {
      if (inDoubleQuote && nextChar === '"') {
        normalized += "'";
        spans.push({ start: index, end: index + 2 });
        index += 1;
        continue;
      }
      inDoubleQuote = !inDoubleQuote;
      normalized += "'";
      spans.push({ start: index, end: index + 1 });
      continue;
    }

    if (inSingleQuote || inDoubleQuote) {
      if (/\s/.test(char)) continue;
      normalized += char.toLowerCase();
      spans.push({ start: index, end: index + 1 });
      continue;
    }

    if (/\s/.test(char)) continue;

    if (isRangeMatchQuoteChar(char)) {
      const nextQuote = chars[index + 1];
      if (nextQuote && isRangeMatchQuoteChar(nextQuote) && char === nextQuote) {
        normalized += "'";
        spans.push({ start: index, end: index + 2 });
        index += 1;
        continue;
      }
      normalized += "'";
      spans.push({ start: index, end: index + 1 });
      continue;
    }

    normalized += char.toLowerCase();
    spans.push({ start: index, end: index + 1 });
  }

  return { normalized, spans };
}

function prepareNeedleText(text) {
  return String(text ?? "").trim().replace(/;\s*$/, "");
}

function canonicalizeNeedle(text) {
  return buildCanonicalTextIndexMap(prepareNeedleText(text)).normalized;
}

function stripTrailingLimitSuffix(normalized) {
  return normalized.replace(/\blimit\s+\d+(?:\s*,\s*\d+)?\s*;?\s*$/i, "");
}

function findNormalizedRange(haystack, spans, normalizedNeedle) {
  if (!normalizedNeedle) return null;

  let normalizedIndex = haystack.indexOf(normalizedNeedle);
  if (normalizedIndex >= 0) {
    return { normalizedIndex, matchLength: normalizedNeedle.length };
  }

  const haystackWithoutLimit = stripTrailingLimitSuffix(haystack);
  normalizedIndex = haystackWithoutLimit.indexOf(normalizedNeedle);
  if (normalizedIndex >= 0) {
    return { normalizedIndex, matchLength: normalizedNeedle.length };
  }

  if (haystackWithoutLimit.startsWith(normalizedNeedle)) {
    return { normalizedIndex: 0, matchLength: normalizedNeedle.length };
  }

  return null;
}

function findAnswerTextRangeFrom(content, answerText, searchStart = 0) {
  const needle = prepareNeedleText(answerText);
  if (!needle) return null;

  const slice = content.slice(searchStart);
  const exactIndex = slice.indexOf(needle);
  if (exactIndex >= 0) {
    const start = searchStart + exactIndex;
    return { start, end: start + needle.length };
  }

  const { normalized: haystack, spans } = buildCanonicalTextIndexMap(slice);
  const normalizedNeedle = canonicalizeNeedle(needle);
  const matched = findNormalizedRange(haystack, spans, normalizedNeedle);
  if (!matched) return null;

  const startSpan = spans[matched.normalizedIndex];
  const endSpan = spans[matched.normalizedIndex + matched.matchLength - 1];
  if (!startSpan || !endSpan) return null;

  return {
    start: searchStart + startSpan.start,
    end: searchStart + endSpan.end,
  };
}

function splitSqlStatements(text) {
  const statements = [];
  let current = "";
  let inSingleQuote = false;
  let inDoubleQuote = false;

  for (const char of String(text ?? "")) {
    if (char === "'" && !inDoubleQuote) {
      inSingleQuote = !inSingleQuote;
      current += char;
      continue;
    }
    if (char === '"' && !inSingleQuote) {
      inDoubleQuote = !inDoubleQuote;
      current += char;
      continue;
    }
    if (char === ";" && !inSingleQuote && !inDoubleQuote) {
      const statement = current.trim();
      if (statement) statements.push(statement);
      current = "";
      continue;
    }
    current += char;
  }

  const tail = current.trim();
  if (tail) statements.push(tail);
  return statements;
}

function looksLikeSqlAnswer(text) {
  return /\b(select|insert|update|delete|set|create|drop|alter|with)\b/i.test(String(text ?? ""));
}

function findStatementRanges(content, answerText) {
  const statements = splitSqlStatements(answerText);
  if (!statements.length) return [];

  const ranges = [];
  let searchStart = 0;

  for (const statement of statements) {
    const range = findAnswerTextRangeFrom(content, statement, searchStart);
    if (!range) continue;
    ranges.push(range);
    searchStart = range.end;
  }

  return ranges;
}

function findStatementSequenceRange(content, answerText) {
  const ranges = findStatementRanges(content, answerText);
  if (!ranges.length) return null;
  return {
    start: ranges[0].start,
    end: ranges[ranges.length - 1].end,
  };
}

export function findAnswerTextRanges(content, answerText) {
  const needle = prepareNeedleText(answerText);
  if (!needle || !content) return [];

  let range = findAnswerTextRangeFrom(content, needle, 0);
  if (range) return [range];

  const lines = needle.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length > 1) {
    const lineRanges = [];
    let searchStart = 0;
    for (const line of lines) {
      const lineRange = findAnswerTextRangeFrom(content, line, searchStart);
      if (!lineRange) break;
      lineRanges.push(lineRange);
      searchStart = lineRange.end;
    }
    if (lineRanges.length === lines.length) return lineRanges;
  }

  if (looksLikeSqlAnswer(needle)) {
    const statementRanges = findStatementRanges(content, needle);
    if (statementRanges.length) return statementRanges;
  }

  return [];
}

export function findAnswerTextRange(content, answerText) {
  const ranges = findAnswerTextRanges(content, answerText);
  if (!ranges.length) return null;
  return {
    start: ranges[0].start,
    end: ranges[ranges.length - 1].end,
  };
}

export function buildHighlightedSubmissionParts(student, answers) {
  const content = student?.content ?? "";
  if (!content) return [{ key: "empty", text: "暂无学生作业原文", questionId: null }];

  const ranges = [];
  answers.forEach((answer) => {
    const answerText = String(answer.answer_text ?? "").trim();
    if (!answerText) return;
    findAnswerTextRanges(content, answerText).forEach((range) => {
      ranges.push({
        start: range.start,
        end: range.end,
        questionId: answer.question_id,
      });
    });
  });
  ranges.sort((left, right) => left.start - right.start);

  const parts = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start < cursor) return;
    if (range.start > cursor) {
      parts.push({ key: `text-${index}-${cursor}`, text: content.slice(cursor, range.start), questionId: null });
    }
    parts.push({
      key: `answer-${range.questionId}-${range.start}`,
      text: content.slice(range.start, range.end),
      questionId: range.questionId,
    });
    cursor = range.end;
  });
  if (cursor < content.length) {
    parts.push({ key: `text-tail-${cursor}`, text: content.slice(cursor), questionId: null });
  }
  return parts.length ? parts : [{ key: "all", text: content, questionId: null }];
}
