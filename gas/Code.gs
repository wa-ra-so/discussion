/**
 * 商談解析システム（Google Apps Script 版）
 *
 * 文字起こし済みの商談テキストを、外部AI APIを一切使わずキーワード・
 * ルールベースで構造化し、このスクリプトが紐づくスプレッドシートに
 * 法人/店舗別に蓄積する。Web アプリとしてデプロイすることで、チーム全員が
 * 専用URLからアクセスできる。Fly.io等の外部ホスティングも、Gemini/Claude
 * 等の外部AI APIも一切使わず、Googleアカウントの中だけで完結する。
 *
 * ルールベースゆえの制約: 「人手が足りなくて困っている」のような
 * キーワードを含む明示的な言い回しは拾えるが、遠回しな表現や文脈依存の
 * 課題までは拾えない。DXソリューション提案も、検出したカテゴリに応じた
 * 定型文からの選択になる（AIによる商談内容に即した提案ではない）。
 */

const SHEET_MEETINGS = 'Meetings';
const SHEET_ISSUES = 'PriorityIssues';

const MEETINGS_HEADERS = [
  'meeting_id', 'corporate_name', 'company_name', 'contact_name',
  'meeting_date', 'created_at', 'confidence_score', 'summary',
  'discussions_json', 'priority_issues_json', 'dx_solutions_json', 'notes',
];

const ISSUES_HEADERS = [
  'meeting_id', 'corporate_name', 'company_name', 'category', 'issue',
  'priority', 'meeting_date',
];

// ============================================================================
// Web アプリのエントリーポイント
// ============================================================================
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('商談解析システム')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ============================================================================
// テキスト解析（ルールベース抽出）
// ============================================================================
/**
 * @param {{transcript:string, companyName:string, corporateName?:string,
 *          contactName?:string, meetingDate?:string, notes?:string}} params
 * @return {object} 解析結果（クライアント表示用）
 */
function analyzeTranscript(params) {
  const transcript = (params.transcript || '').trim();
  const companyName = (params.companyName || '').trim();

  if (transcript.length < 10) {
    throw new Error('文字起こしテキストが短すぎます（10文字以上必要です）');
  }
  if (!companyName) {
    throw new Error('店舗名は必須です');
  }

  const structured = extractRuleBased_(transcript);
  const record = buildRecord_(structured, params);

  saveRecord_(record);

  return record;
}

// ============================================================================
// ルールベース抽出エンジン（外部AI APIなし）
// ============================================================================

// カテゴリ判定用キーワード（①採用・人手 ②集客・売上 ③予約・業務効率 ④インバウンド集客）
const CATEGORY_KEYWORDS_ = {
  recruitment: ['採用', '人手', 'スタッフ', '求人', 'アルバイト', 'パート', '社員', '人材', '離職', '欠員', '募集'],
  sales: ['売上', '客単価', '集客', '客数', '稼働率', '客層', '来店', '売り上げ', '回転率', '席稼働'],
  booking_efficiency: ['予約', '発注', 'オペレーション', '電話対応', 'ダブルブッキング', 'システム', '業務効率', '注文', 'レジ'],
  inbound: ['インバウンド', '外国人', '多言語', '英語対応', '海外', '訪日'],
};

// 課題を示唆する表現（このいずれかを含む文だけを priority_issues の候補にする）
// 「問題なく」「悪くない」のような否定表現を誤検出しないよう、
// 単純な部分一致で安全な語のみを採用している（例: 「悪く」は「悪くない」に
// マッチしてしまうため避け、「悪い」のみ採用）
const ISSUE_KEYWORDS_ = [
  '課題', '困っ', '難し', '不足', '足りない', '対応できて', 'できていない',
  '悩んでいる', '悩み', '厳しい', '減って', '下がって', '来ない', '応募がない',
  '苦労', '手が回らない', '間に合わない', '負担', '大変', '悪い', 'ミス',
];

// 優先度を引き上げる強調表現
const PRIORITY_INTENSIFIERS_ = ['かなり', 'とても', '非常に', '深刻', '毎日', '常に', 'すごく', '大きな', '相当'];

// カテゴリごとの定型DXソリューション（AIによる個別提案の代わり）
const DX_SOLUTIONS_BY_CATEGORY_ = {
  recruitment: { bucket: 'recruitment_market_development', text: '食べログ求人による人材募集の強化' },
  sales: { bucket: 'revenue_maximization', text: '食べログ有料プランでの露出強化・ネット予約導線の最適化' },
  booking_efficiency: { bucket: 'efficiency_cost_reduction', text: 'ネット予約・発注システム連携による業務時間の削減' },
  inbound: { bucket: 'revenue_maximization', text: '食べログの多言語掲載・インバウンド集客支援の活用' },
};

const CATEGORY_ORDER_ = ['recruitment', 'sales', 'booking_efficiency', 'inbound'];

/**
 * 文字起こしテキストをキーワードベースで解析し、Gemini/Claude版と
 * 同じ形（discussions/priority_issues/dx_solutions/summary/confidence_score）
 * の構造化データを返す。
 */
function extractRuleBased_(transcript) {
  const sentences = splitSentences_(transcript);

  const discussions = {};
  const priorityIssues = [];
  const matchedCategories = {};

  CATEGORY_ORDER_.forEach(function (category) {
    const keywords = CATEGORY_KEYWORDS_[category];
    const categorySentences = sentences.filter(function (s) { return containsAny_(s, keywords); });
    const issueSentences = categorySentences.filter(function (s) { return containsAny_(s, ISSUE_KEYWORDS_); });

    if (categorySentences.length > 0) {
      matchedCategories[category] = true;
      discussions[category] = {
        assumed_issues: issueSentences.length > 0 ? issueSentences.join(' ') : null,
      };
    }

    issueSentences.forEach(function (sentence) {
      let priority = 3;
      if (containsAny_(sentence, PRIORITY_INTENSIFIERS_)) priority += 1;
      if (issueSentences.length > 1) priority += 1;
      priority = Math.max(1, Math.min(5, priority));

      priorityIssues.push({ category: category, issue: sentence, priority: priority });
    });
  });

  const dxSolutions = { revenue_maximization: [], efficiency_cost_reduction: [], recruitment_market_development: [] };
  Object.keys(matchedCategories).forEach(function (category) {
    const solution = DX_SOLUTIONS_BY_CATEGORY_[category];
    if (solution && dxSolutions[solution.bucket].indexOf(solution.text) === -1) {
      dxSolutions[solution.bucket].push(solution.text);
    }
  });

  const summary = priorityIssues.length > 0
    ? '検出された課題: ' + priorityIssues.map(function (i) { return i.issue; }).join(' / ')
    : 'キーワードベースの解析では明確な課題は検出されませんでした。文字起こし内容を直接ご確認ください。';

  // 検出網羅率（4カテゴリ中いくつでキーワードがヒットしたか）を参考値として返す。
  // AIによる意味的な確信度ではない点に注意。
  const confidenceScore = Object.keys(matchedCategories).length / CATEGORY_ORDER_.length;

  return {
    discussions: discussions,
    priority_issues: priorityIssues,
    dx_solutions: dxSolutions,
    summary: summary,
    confidence_score: confidenceScore,
  };
}

function splitSentences_(text) {
  return text
    .split(/[。\n]/)
    .map(function (s) { return s.trim(); })
    .filter(function (s) { return s.length > 0; });
}

function containsAny_(text, keywords) {
  return keywords.some(function (kw) { return text.indexOf(kw) !== -1; });
}

function buildRecord_(structured, params) {
  const now = new Date();
  const meetingId = Utilities.formatDate(now, 'Asia/Tokyo', 'yyyyMMdd_HHmm') +
    '_' + params.companyName.replace(/\s+/g, '_');

  const priorityIssues = Array.isArray(structured.priority_issues) ? structured.priority_issues : [];
  const dxSolutions = structured.dx_solutions || {};

  return {
    meeting_id: meetingId,
    company_name: params.companyName,
    corporate_name: params.corporateName || null,
    contact_name: params.contactName || null,
    meeting_date: params.meetingDate || now.toISOString(),
    created_at: now.toISOString(),
    confidence_score: typeof structured.confidence_score === 'number' ? structured.confidence_score : 0,
    summary: structured.summary || '',
    discussions: structured.discussions || {},
    priority_issues: priorityIssues,
    dx_solutions: dxSolutions,
    notes: params.notes || null,
  };
}

// ============================================================================
// スプレッドシート I/O
// ============================================================================
function getSheet_(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/**
 * レコードを Meetings / PriorityIssues シートに書き込む。
 * 複数人が同時に実行してもズレないよう LockService で排他制御する。
 */
function saveRecord_(record) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const meetingsSheet = getSheet_(SHEET_MEETINGS, MEETINGS_HEADERS);
    meetingsSheet.appendRow([
      record.meeting_id,
      record.corporate_name || '',
      record.company_name,
      record.contact_name || '',
      record.meeting_date,
      record.created_at,
      record.confidence_score,
      record.summary,
      JSON.stringify(record.discussions),
      JSON.stringify(record.priority_issues),
      JSON.stringify(record.dx_solutions),
      record.notes || '',
    ]);

    if (record.priority_issues.length > 0) {
      const issuesSheet = getSheet_(SHEET_ISSUES, ISSUES_HEADERS);
      const rows = record.priority_issues.map(function (issue) {
        return [
          record.meeting_id,
          record.corporate_name || '',
          record.company_name,
          issue.category || '',
          issue.issue || '',
          issue.priority || '',
          record.meeting_date,
        ];
      });
      issuesSheet.getRange(issuesSheet.getLastRow() + 1, 1, rows.length, ISSUES_HEADERS.length).setValues(rows);
    }
  } finally {
    lock.releaseLock();
  }
}

function readSheetAsObjects_(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(name);
  if (!sheet || sheet.getLastRow() < 2) return [];

  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, headers.length).getValues();
  return values.map(function (row) {
    const obj = {};
    headers.forEach(function (h, i) { obj[h] = row[i]; });
    return obj;
  });
}

function getAllMeetings_() {
  return readSheetAsObjects_(SHEET_MEETINGS, MEETINGS_HEADERS);
}

function getAllIssues_() {
  return readSheetAsObjects_(SHEET_ISSUES, ISSUES_HEADERS);
}

// ============================================================================
// 一覧・検索・カルテ（クライアントから google.script.run で呼び出される）
// ============================================================================
function listMeetings(params) {
  params = params || {};
  const meetings = getAllMeetings_();

  if (params.companyName) {
    const filtered = meetings
      .filter(function (m) { return m.company_name === params.companyName; })
      .sort(function (a, b) { return new Date(b.meeting_date) - new Date(a.meeting_date); })
      .slice(0, params.limit || 50);
    return { companyName: params.companyName, meetings: filtered };
  }

  if (params.corporateName) {
    return { corporateName: params.corporateName, stores: getCorporateCard(params.corporateName).stores };
  }

  const corporations = {};
  const companies = {};
  meetings.forEach(function (m) {
    if (m.corporate_name) {
      const c = corporations[m.corporate_name] || { name: m.corporate_name, stores: new Set(), meeting_count: 0, last_meeting: null };
      c.stores.add(m.company_name);
      c.meeting_count += 1;
      if (!c.last_meeting || new Date(m.meeting_date) > new Date(c.last_meeting)) c.last_meeting = m.meeting_date;
      corporations[m.corporate_name] = c;
    }
    const co = companies[m.company_name] || { name: m.company_name, corporate_name: m.corporate_name || null, meeting_count: 0, last_meeting: null };
    co.meeting_count += 1;
    if (!co.corporate_name && m.corporate_name) co.corporate_name = m.corporate_name;
    if (!co.last_meeting || new Date(m.meeting_date) > new Date(co.last_meeting)) co.last_meeting = m.meeting_date;
    companies[m.company_name] = co;
  });

  return {
    corporations: Object.values(corporations).map(function (c) {
      return { name: c.name, store_count: c.stores.size, meeting_count: c.meeting_count, last_meeting: c.last_meeting };
    }),
    companies: Object.values(companies),
  };
}

function searchIssues(query) {
  if (!query || query.length < 2) throw new Error('検索キーワードは2文字以上必要です');
  const q = query.toLowerCase();
  return getAllIssues_()
    .filter(function (row) { return String(row.issue).toLowerCase().indexOf(q) !== -1; })
    .sort(function (a, b) { return new Date(b.meeting_date) - new Date(a.meeting_date); })
    .slice(0, 50);
}

function getCompanyCard(companyName) {
  const meetings = getAllMeetings_()
    .filter(function (m) { return m.company_name === companyName; })
    .sort(function (a, b) { return new Date(b.meeting_date) - new Date(a.meeting_date); });

  if (meetings.length === 0) return null;

  const records = meetings.map(function (m) {
    return {
      meeting_id: m.meeting_id,
      corporate_name: m.corporate_name || null,
      company_name: m.company_name,
      contact_name: m.contact_name || null,
      meeting_date: m.meeting_date,
      confidence_score: m.confidence_score,
      summary: m.summary,
      discussions: safeJsonParse_(m.discussions_json, {}),
      priority_issues: safeJsonParse_(m.priority_issues_json, []),
      dx_solutions: safeJsonParse_(m.dx_solutions_json, {}),
      notes: m.notes || null,
    };
  });

  const issues = getAllIssues_().filter(function (i) { return i.company_name === companyName; });
  const stats = {};
  issues.forEach(function (i) {
    const s = stats[i.category] || { count: 0, total_priority: 0 };
    s.count += 1;
    s.total_priority += Number(i.priority) || 0;
    stats[i.category] = s;
  });
  Object.keys(stats).forEach(function (k) {
    stats[k] = { count: stats[k].count, avg_priority: stats[k].count ? stats[k].total_priority / stats[k].count : 0 };
  });

  return {
    company_name: companyName,
    corporate_name: records[0].corporate_name,
    total_meetings: records.length,
    latest_record: records[0],
    all_records: records,
    stats: stats,
  };
}

function getCorporateCard(corporateName) {
  const meetings = getAllMeetings_().filter(function (m) { return m.corporate_name === corporateName; });
  if (meetings.length === 0) return null;

  const issues = getAllIssues_().filter(function (i) { return i.corporate_name === corporateName; });

  const byStore = {};
  meetings.forEach(function (m) {
    const s = byStore[m.company_name] || { company_name: m.company_name, meeting_count: 0, last_meeting: null };
    s.meeting_count += 1;
    if (!s.last_meeting || new Date(m.meeting_date) > new Date(s.last_meeting)) s.last_meeting = m.meeting_date;
    byStore[m.company_name] = s;
  });

  Object.values(byStore).forEach(function (s) {
    const storeIssues = issues.filter(function (i) { return i.company_name === s.company_name; });
    s.issue_count = storeIssues.length;
    s.has_issues = storeIssues.length > 0;
    const top = storeIssues.sort(function (a, b) { return (Number(b.priority) || 0) - (Number(a.priority) || 0); })[0];
    s.top_issue = top ? top.issue : null;
  });

  return { corporate_name: corporateName, stores: Object.values(byStore) };
}

function safeJsonParse_(text, fallback) {
  try {
    return text ? JSON.parse(text) : fallback;
  } catch (e) {
    return fallback;
  }
}
