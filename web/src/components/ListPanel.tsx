"use client";

import { useEffect, useState } from "react";
import { Card } from "@heroui/react";
import { Button } from "@heroui/react";
import { TextField } from "@heroui/react";
import { Label } from "@heroui/react";
import { Input } from "@heroui/react";
import { Spinner } from "@heroui/react";
import { Alert } from "@heroui/react";
import { Chip } from "@heroui/react";
import { Building2, CalendarX, Users } from "lucide-react";
import { ApiRequestError, listMeetings } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/constants";
import { EmptyState } from "@/components/EmptyState";
import type { CompanySummary, MeetingSummary } from "@/lib/types";

export function ListPanel({ onSelectCompany }: { onSelectCompany: (name: string) => void }) {
  const [filter, setFilter] = useState("");
  const [companies, setCompanies] = useState<CompanySummary[] | null>(null);
  const [meetings, setMeetings] = useState<MeetingSummary[] | null>(null);
  const [activeCompany, setActiveCompany] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCompanies = async () => {
    setIsLoading(true);
    setError(null);
    setActiveCompany(null);
    setMeetings(null);
    try {
      const data = await listMeetings({ limit: 50 });
      setCompanies(data.companies ?? []);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const loadCompanyMeetings = async (companyName: string) => {
    setIsLoading(true);
    setError(null);
    setActiveCompany(companyName);
    try {
      const data = await listMeetings({ companyName, limit: 50 });
      setMeetings(data.meetings ?? []);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredCompanies =
    companies?.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase())) ?? [];

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>商談記録一覧</Card.Title>
          <Card.Description>
            {activeCompany ? `${activeCompany} の商談履歴` : "登録済みの企業一覧"}
          </Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <div className="flex items-end gap-3">
            <TextField.Root
              value={filter}
              onChange={setFilter}
              className="flex flex-1 flex-col gap-1.5"
            >
              <Label>企業名で絞り込み</Label>
              <Input placeholder="レストランA" />
            </TextField.Root>
            {activeCompany && (
              <Button variant="outline" onClick={loadCompanies}>
                企業一覧に戻る
              </Button>
            )}
          </div>

          {error && (
            <Alert.Root status="danger">
              <Alert.Content>
                <Alert.Description>{error}</Alert.Description>
              </Alert.Content>
            </Alert.Root>
          )}

          {isLoading && (
            <div className="flex items-center gap-2 py-8 justify-center text-neutral-500">
              <Spinner /> 読み込み中...
            </div>
          )}

          {!isLoading && !activeCompany && (
            <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
              {filteredCompanies.length === 0 && (
                <EmptyState icon={Building2} message="該当する企業がありません" />
              )}
              {filteredCompanies.map((company) => (
                <button
                  key={company.company_id}
                  onClick={() => loadCompanyMeetings(company.name)}
                  className="flex cursor-pointer items-center justify-between gap-4 rounded-lg py-3 text-left transition-colors duration-150 hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)]"
                >
                  <div className="flex items-center gap-3">
                    <Building2 className="h-5 w-5 text-[var(--accent)]" />
                    <div>
                      <p className="font-medium">{company.name}</p>
                      <p className="text-xs text-neutral-500">
                        最終商談: {formatDate(company.last_meeting)}
                      </p>
                    </div>
                  </div>
                  <Chip size="sm">
                    <Chip.Label>
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3 w-3" /> {company.meeting_count}件
                      </span>
                    </Chip.Label>
                  </Chip>
                </button>
              ))}
            </div>
          )}

          {!isLoading && activeCompany && (
            <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
              {(meetings?.length ?? 0) === 0 && (
                <EmptyState icon={CalendarX} message="商談記録がありません" />
              )}
              {meetings?.map((meeting) => (
                <div key={meeting.meeting_uuid} className="flex flex-col gap-1 py-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{formatDate(meeting.meeting_date)}</p>
                    <Chip size="sm" color={confidenceColor(meeting.confidence_score)}>
                      <Chip.Label>{formatPercent(meeting.confidence_score)}</Chip.Label>
                    </Chip>
                  </div>
                  <p className="text-sm text-neutral-500">
                    接触者: {meeting.contact_name ?? "不明"}
                  </p>
                  {meeting.summary && <p className="text-sm">{meeting.summary}</p>}
                </div>
              ))}
              <div className="pt-4">
                <Button onClick={() => onSelectCompany(activeCompany)}>
                  法人カルテを見る
                </Button>
              </div>
            </div>
          )}
        </Card.Content>
      </Card.Root>
    </div>
  );
}

function confidenceColor(score: number | null): "success" | "warning" | "danger" | "default" {
  if (score === null || score === undefined) return "default";
  if (score >= 0.8) return "success";
  if (score >= 0.5) return "warning";
  return "danger";
}
