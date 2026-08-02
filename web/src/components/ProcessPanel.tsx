"use client";

import { useState } from "react";
import { Card } from "@heroui/react";
import { Button } from "@heroui/react";
import { TextField } from "@heroui/react";
import { Label } from "@heroui/react";
import { Input } from "@heroui/react";
import { TextArea } from "@heroui/react";
import { Alert } from "@heroui/react";
import { Chip } from "@heroui/react";
import { Spinner } from "@heroui/react";
import { CheckCircle2, XCircle, FileText } from "lucide-react";
import { ApiRequestError, analyzeTranscript } from "@/lib/api";
import { categoryLabel } from "@/lib/constants";
import { PriorityIndicator } from "@/components/PriorityIndicator";
import type { ProcessResult } from "@/lib/types";

const MIN_TRANSCRIPT_LENGTH = 10;

export function ProcessPanel() {
  const [transcript, setTranscript] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [corporateName, setCorporateName] = useState("");
  const [contactName, setContactName] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessResult | null>(null);

  const handleSubmit = async () => {
    if (transcript.trim().length < MIN_TRANSCRIPT_LENGTH || !companyName.trim()) {
      setError("文字起こしテキスト（10文字以上）と店舗名は必須です");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeTranscript({
        transcript: transcript.trim(),
        companyName: companyName.trim(),
        corporateName: corporateName.trim() || undefined,
        contactName: contactName.trim() || undefined,
        meetingDate: meetingDate || undefined,
        notes: notes.trim() || undefined,
      });
      setResult(data);
      setTranscript("");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(`サーバーエラー (HTTP ${err.status}): ${err.message}`);
      } else if (err instanceof TypeError) {
        setError(`サーバーに接続できませんでした（${err.message}）。しばらくしてから再度お試しください。`);
      } else {
        const message = err instanceof Error ? err.message : String(err);
        setError(`処理中に予期しないエラーが発生しました: ${message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>商談テキストを解析</Card.Title>
          <Card.Description>
            文字起こし済みの商談テキストを貼り付けると、Claude API が自動でディスカッション項目を抽出します
          </Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-5">
          <TextField.Root
            value={transcript}
            onChange={setTranscript}
            isRequired
            className="flex flex-col gap-1.5"
          >
            <Label className="flex items-center gap-1.5">
              <FileText className="h-4 w-4" />
              文字起こしテキスト
            </Label>
            <TextArea
              placeholder="商談の文字起こしテキストをここに貼り付けてください"
              rows={10}
            />
          </TextField.Root>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField.Root
              value={companyName}
              onChange={setCompanyName}
              isRequired
              className="flex flex-col gap-1.5"
            >
              <Label>店舗名</Label>
              <Input placeholder="レストランA 渋谷店" />
            </TextField.Root>

            <TextField.Root
              value={corporateName}
              onChange={setCorporateName}
              className="flex flex-col gap-1.5"
            >
              <Label>法人名（複数店舗経営の場合のみ）</Label>
              <Input placeholder="株式会社レストランA" />
            </TextField.Root>

            <TextField.Root
              value={contactName}
              onChange={setContactName}
              className="flex flex-col gap-1.5"
            >
              <Label>接触者氏名</Label>
              <Input placeholder="山田太郎" />
            </TextField.Root>

            <TextField.Root className="flex flex-col gap-1.5">
              <Label>商談日時</Label>
              <Input
                type="datetime-local"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
              />
            </TextField.Root>
          </div>

          <TextField.Root
            value={notes}
            onChange={setNotes}
            className="flex flex-col gap-1.5"
          >
            <Label>補足メモ</Label>
            <TextArea placeholder="商談の背景や特記事項があれば記入してください" rows={3} />
          </TextField.Root>

          {error && (
            <Alert.Root status="danger">
              <Alert.Indicator>
                <XCircle className="h-4 w-4" />
              </Alert.Indicator>
              <Alert.Content>
                <Alert.Description>{error}</Alert.Description>
              </Alert.Content>
            </Alert.Root>
          )}

          <Button
            onClick={handleSubmit}
            isDisabled={transcript.trim().length < MIN_TRANSCRIPT_LENGTH || !companyName.trim() || isLoading}
            className="self-start"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Spinner size="sm" /> 解析中...
              </span>
            ) : (
              "解析を開始"
            )}
          </Button>
        </Card.Content>
      </Card.Root>

      {result && (
        <Card.Root>
          <Card.Header>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <Card.Title>解析完了</Card.Title>
            </div>
            <Card.Description>Meeting ID: {result.meeting_id}</Card.Description>
          </Card.Header>
          <Card.Content className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-4 text-sm">
              <div>
                <p className="text-neutral-500">店舗名</p>
                <p className="font-medium">{result.company_name}</p>
              </div>
              {result.corporate_name && (
                <div>
                  <p className="text-neutral-500">法人名</p>
                  <p className="font-medium">{result.corporate_name}</p>
                </div>
              )}
              <div>
                <p className="text-neutral-500">接触者</p>
                <p className="font-medium">{result.contact_name}</p>
              </div>
              <div>
                <p className="text-neutral-500">信頼度</p>
                <p className="font-medium">{Math.round(result.confidence_score * 100)}%</p>
              </div>
            </div>

            {result.summary && (
              <div>
                <p className="mb-1 text-sm text-neutral-500">要約</p>
                <p className="text-sm">{result.summary}</p>
              </div>
            )}

            {result.priority_issues.length > 0 && (
              <div>
                <p className="mb-2 text-sm text-neutral-500">優先課題</p>
                <ul className="flex flex-col gap-2">
                  {result.priority_issues.map((issue, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <Chip size="sm">
                        <Chip.Label>{categoryLabel(issue.category)}</Chip.Label>
                      </Chip>
                      <span>{issue.issue}</span>
                      <PriorityIndicator value={issue.priority} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card.Content>
        </Card.Root>
      )}
    </div>
  );
}
