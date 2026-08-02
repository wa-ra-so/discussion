/**
 * 商談解析システム（Google Apps Script 版）
 *
 * 文字起こし済みの商談テキストを Gemini API で構造化し、
 * このスクリプトが紐づくスプレッドシートに法人/店舗別に蓄積する。
 * Web アプリとしてデプロイすることで、チーム全員が専用URLからアクセスできる
 * （個々人が Gemini アカウントを持つ必要はなく、スクリプトプロパティに
 * 保存した1つの API キーを共有する）。
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

const DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash';

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
// テキスト解析（Gemini API 呼び出し）
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

  const structured = callGemini_(transcript, params);
  const record = buildRecord_(structured, params);

  saveRecord_(record);

  return record;
}

/**
 * Gemini API を呼び出し、構造化 JSON を取得する
 */
function callGemini_(transcript, params) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) {
    throw new Error(
      'GEMINI_API_KEY が設定されていません。' +
      'スクリプトエディタの「プロジェクトの設定」→「スクリプト プロパティ」で設定してください。'
    );
  }
  const model = PropertiesService.getScriptProperties().getProperty('GEMINI_MODEL') || DEFAULT_GEMINI_MODEL;

  const systemPrompt = buildSystemPrompt_();
  const userPrompt = buildUserPrompt_(transcript, params);

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
    model + ':generateContent?key=' + encodeURIComponent(apiKey);

  const payload = {
    systemInstruction: { parts: [{ text: systemPrompt }] },
    contents: [{ role: 'user', parts: [{ text: userPrompt }] }],
    generationConfig: {
      responseMimeType: 'application/json',
      temperature: 0.2,
    },
  };

  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });

  const status = response.getResponseCode();
  const body = response.getContentText();

  if (status < 200 || status >= 300) {
    throw new Error('Gemini API エラー (HTTP ' + status + '): ' + body.slice(0, 500));
  }

  const data = JSON.parse(body);
  const candidate = data.candidates && data.candidates[0];
  const text = candidate && candidate.content && candidate.content.parts
    && candidate.content.parts[0] && candidate.content.parts[0].text;

  if (!text) {
    throw new Error('Gemini からの応答が空です: ' + body.slice(0, 500));
  }

  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error('Gemini の応答を JSON として解析できませんでした: ' + text.slice(0, 500));
  }
}

function buildSystemPrompt_() {
  return [
    'あなたは食べログの営業ヒアリング記録を分析するAIです。',
    '',
    '商談音声の書き起こしテキストが与えられます。',
    '以下の6つのディスカッション項目から情報を抽出し、JSONフォーマットで返してください：',
    '',
    '1. 採用・人手（recruitment）：スタッフ構成、採用課題、求人施策',
    '2. 集客・売上（sales）：客単価、席稼働率、客層、売上施策',
    '3. 予約・業務効率（booking_efficiency）：予約システム、発注業務、オペレーション課題',
    '4. インバウンド集客（inbound）：外国人客対応、多言語対応状況',
    '5. 優先課題（priority_issues）：複数の課題を優先度付け',
    '6. DXソリューション提案（dx_solutions）：食べログの提案ソリューション',
    '',
    '【重要】',
    '- 確実に抽出できた情報のみを記入してください',
    '- 推測や補完は避けてください',
    '- 不確実な情報や曖昧な箇所は記入しないでください',
    '- JSON フォーマットで返してください（マークダウンのコードブロックは不要、JSON本文のみ）',
    '',
    '【JSON スキーマ】',
    JSON.stringify({
      discussions: {
        recruitment: {
          assumed_issues: 'string or null',
          current_staff: { employees: 'number or null', part_time: 'number or null' },
          ideal_staff: { employees: 'number or null', part_time: 'number or null' },
          hiring_needs: 'string or null',
          current_initiatives: 'string or null',
        },
        sales: {
          average_customer_spend: { lunch: 'number or null', dinner: 'number or null' },
          seat_utilization: { weekday: 'number or null', weekend: 'number or null' },
          customer_segment: 'string or null',
          current_initiatives: 'string or null',
        },
        booking_efficiency: {
          current_reservation_method: ['string'],
          phone_response: { frequency: 'string or null', daily_calls: 'number or null' },
          daily_ordering_time: 'number or null',
          ordering_responsible: 'string or null',
        },
        inbound: {
          monthly_foreign_guests: 'number or null',
          multilingual_support: 'string or null',
        },
      },
      priority_issues: [{ category: 'string', issue: 'string', priority: 'number (1-5)' }],
      dx_solutions: {
        revenue_maximization: ['string'],
        efficiency_cost_reduction: ['string'],
        recruitment_market_development: ['string'],
      },
      summary: 'string',
      confidence_score: 'number (0.0-1.0)',
    }, null, 2),
  ].join('\n');
}

function buildUserPrompt_(transcript, params) {
  return [
    '【商談情報】',
    '店舗名：' + params.companyName,
    '法人名：' + (params.corporateName || '不明（単一店舗経営の可能性）'),
    '接触者：' + (params.contactName || '不明'),
    '日時：' + (params.meetingDate || '不明'),
    '',
    '【文字起こしテキスト】',
    transcript,
    '',
    '【指示】',
    '上記の商談内容から、6つのディスカッション項目への情報抽出を行い、',
    'JSON フォーマットで返してください。',
  ].join('\n');
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
