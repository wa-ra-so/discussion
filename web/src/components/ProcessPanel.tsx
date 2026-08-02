"use client";

import { useEffect, useRef, useState } from "react";
import { Card } from "@heroui/react";
import { Button } from "@heroui/react";
import { TextField } from "@heroui/react";
import { Label } from "@heroui/react";
import { Input } from "@heroui/react";
import { TextArea } from "@heroui/react";
import { Alert } from "@heroui/react";
import { Chip } from "@heroui/react";
import { ProgressBar } from "@heroui/react";
import { Spinner } from "@heroui/react";
import { UploadCloud, FileAudio, CheckCircle2, XCircle } from "lucide-react";
import { ApiRequestError, getProcessStatus, processAudio } from "@/lib/api";
import { categoryLabel } from "@/lib/constants";
import { PriorityIndicator } from "@/components/PriorityIndicator";
import type { ProcessResult } from "@/lib/types";

const SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".flac", ".ogg"];
const MAX_FILE_SIZE = 100 * 1024 * 1024;
const POLL_INTERVAL_MS = 3000;

export function ProcessPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [corporateName, setCorporateName] = useState("");
  const [contactName, setContactName] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [notes, setNotes] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const validateAndSetFile = (candidate: File | undefined) => {
    if (!candidate) return;
    const ext = candidate.name.slice(candidate.name.lastIndexOf(".")).toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setError(`未対応の形式です: ${ext}（対応形式: ${SUPPORTED_EXTENSIONS.join(", ")}）`);
      return;
    }
    if (candidate.size > MAX_FILE_SIZE) {
      setError("ファイルサイズが100MBを超えています");
      return;
    }
    setError(null);
    setFile(candidate);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    validateAndSetFile(e.dataTransfer.files?.[0]);
  };

  const handleApiError = (err: unknown) => {
    if (err instanceof ApiRequestError) {
      setError(`サーバーエラー (HTTP ${err.status}): ${err.message}`);
    } else if (err instanceof TypeError) {
      // fetch() 自体が失敗（サーバー未応答・CORSブロック・タイムアウトなど）
      setError(
        `サーバーに接続できませんでした（${err.message}）。バックエンドが起動しているか、` +
          "CORS設定を確認してください。",
      );
    } else {
      const message = err instanceof Error ? err.message : String(err);
      setError(`処理中に予期しないエラーが発生しました: ${message}`);
    }
  };

  const pollJobStatus = (jobId: string) => {
    pollTimeoutRef.current = setTimeout(async () => {
      try {
        const status = await getProcessStatus(jobId);
        if (status.status === "pending") {
          pollJobStatus(jobId);
          return;
        }
        setIsLoading(false);
        if (status.status === "completed" && status.result) {
          setResult(status.result);
          setFile(null);
          if (fileInputRef.current) fileInputRef.current.value = "";
        } else {
          setError(status.error ?? "音声処理に失敗しました");
        }
      } catch (err) {
        setIsLoading(false);
        handleApiError(err);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleSubmit = async () => {
    if (!file || !companyName.trim()) {
      setError("音声ファイルと店舗名は必須です");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const { job_id } = await processAudio({
        file,
        companyName: companyName.trim(),
        corporateName: corporateName.trim() || undefined,
        contactName: contactName.trim() || undefined,
        meetingDate: meetingDate || undefined,
        notes: notes.trim() || undefined,
      });
      pollJobStatus(job_id);
    } catch (err) {
      setIsLoading(false);
      handleApiError(err);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>商談音声を処理</Card.Title>
          <Card.Description>
            音声ファイルをアップロードすると、Whisper と Claude API が自動でディスカッション項目を抽出します
          </Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-5">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-10 text-center transition ${
              isDragging
                ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                : "border-neutral-300 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900/50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={SUPPORTED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(e) => validateAndSetFile(e.target.files?.[0])}
            />
            {file ? (
              <>
                <FileAudio className="h-8 w-8 text-blue-600" />
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-neutral-500">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB — クリックして変更
                </p>
              </>
            ) : (
              <>
                <UploadCloud className="h-8 w-8 text-neutral-400" />
                <p className="font-medium">音声ファイルをドラッグ&ドロップ</p>
                <p className="text-sm text-neutral-500">
                  または クリックして選択（MP3 / WAV / M4A / FLAC / OGG、最大100MB）
                </p>
              </>
            )}
          </div>

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

          {isLoading && (
            <div className="flex flex-col gap-2">
              <ProgressBar.Root isIndeterminate>
                <ProgressBar.Track>
                  <ProgressBar.Fill />
                </ProgressBar.Track>
              </ProgressBar.Root>
              <p className="flex items-center gap-2 text-sm text-neutral-500">
                <Spinner size="sm" /> 音声解析中です（数十秒〜数分かかる場合があります）…
              </p>
            </div>
          )}

          <Button
            onClick={handleSubmit}
            isDisabled={!file || !companyName.trim() || isLoading}
            className="self-start"
          >
            {isLoading ? "処理中..." : "解析を開始"}
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
