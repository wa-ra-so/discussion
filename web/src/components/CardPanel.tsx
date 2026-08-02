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
import { Search, Building2 } from "lucide-react";
import { ApiRequestError, getCompanyCard } from "@/lib/api";
import { categoryColor, categoryLabel, formatDate } from "@/lib/constants";
import { PriorityIndicator } from "@/components/PriorityIndicator";
import type { CardResponse } from "@/lib/types";

type RecruitmentSection = {
  assumed_issues?: string;
  current_staff?: { employees?: number; part_time?: number };
  ideal_staff?: { employees?: number; part_time?: number };
  desired_talent?: string;
  hiring_timeline?: string;
  current_initiatives?: string;
};

type SalesSection = {
  assumed_issues?: string;
  average_customer_spend?: { lunch?: number; dinner?: number };
  seat_utilization?: { weekday?: number; weekend?: number };
  customer_segment?: string;
  current_initiatives?: string;
};

type BookingSection = {
  assumed_issues?: string;
  phone_response?: { frequency?: string; daily_calls?: number };
  daily_ordering_time?: number;
  ordering_responsible?: string;
};

type InboundSection = {
  assumed_issues?: string;
  monthly_foreign_guests?: number;
  multilingual_support?: string;
};

export function CardPanel({
  initialCompany,
  onCompanyLoaded,
}: {
  initialCompany?: string | null;
  onCompanyLoaded?: () => void;
}) {
  const [companyName, setCompanyName] = useState(initialCompany ?? "");
  const [card, setCard] = useState<CardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCard = async (name: string) => {
    if (!name.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getCompanyCard(name.trim());
      setCard(data);
    } catch (err) {
      setCard(null);
      setError(
        err instanceof ApiRequestError
          ? err.status === 404
            ? `'${name}' の商談記録はありません`
            : err.message
          : "取得に失敗しました",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (initialCompany) {
      setCompanyName(initialCompany);
      loadCard(initialCompany);
      onCompanyLoaded?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCompany]);

  const latest = card?.latest_record;
  const discussions = (latest?.discussions ?? {}) as {
    recruitment?: RecruitmentSection;
    sales?: SalesSection;
    booking_efficiency?: BookingSection;
    inbound?: InboundSection;
  };

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>法人カルテ</Card.Title>
          <Card.Description>企業名を指定して商談履歴を集約表示します</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <div className="flex items-end gap-3">
            <TextField.Root
              value={companyName}
              onChange={setCompanyName}
              className="flex flex-1 flex-col gap-1.5"
            >
              <Label>店舗名</Label>
              <Input
                placeholder="レストランA"
                onKeyDown={(e) => {
                  if (e.key === "Enter") loadCard(companyName);
                }}
              />
            </TextField.Root>
            <Button onClick={() => loadCard(companyName)} isDisabled={isLoading}>
              <Search className="mr-1 h-4 w-4" /> カルテ表示
            </Button>
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
        </Card.Content>
      </Card.Root>

      {card && latest && (
        <>
          <Card.Root>
            <Card.Header>
              <div className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-blue-600" />
                <Card.Title>{card.company_name}</Card.Title>
              </div>
              <Card.Description>
                接触者: {latest.company_info.contact_name} ／ 商談件数: {card.total_meetings}件 ／
                最終更新: {formatDate(card.generated_at)}
              </Card.Description>
            </Card.Header>
            <Card.Content className="flex flex-col gap-3">
              <p className="text-sm font-medium text-neutral-500">主要な経営課題</p>
              <ul className="flex flex-col gap-2">
                {latest.priority_issues.map((issue, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <Chip size="sm" color={categoryColor(issue.category)}>
                      <Chip.Label>{categoryLabel(issue.category)}</Chip.Label>
                    </Chip>
                    <span>{issue.issue}</span>
                    <PriorityIndicator value={issue.priority} />
                  </li>
                ))}
                {latest.priority_issues.length === 0 && (
                  <li className="text-sm text-neutral-500">記録なし</li>
                )}
              </ul>
            </Card.Content>
          </Card.Root>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {discussions.recruitment && (
              <Card.Root>
                <Card.Header>
                  <Card.Title>採用・人手</Card.Title>
                </Card.Header>
                <Card.Content className="flex flex-col gap-1.5 text-sm">
                  <Field label="課題" value={discussions.recruitment.assumed_issues} />
                  <Field
                    label="現在の体制"
                    value={staffLine(discussions.recruitment.current_staff)}
                  />
                  <Field
                    label="理想の体制"
                    value={staffLine(discussions.recruitment.ideal_staff)}
                  />
                  <Field label="ほしい人材" value={discussions.recruitment.desired_talent} />
                  <Field label="施策" value={discussions.recruitment.current_initiatives} />
                </Card.Content>
              </Card.Root>
            )}

            {discussions.sales && (
              <Card.Root>
                <Card.Header>
                  <Card.Title>集客・売上</Card.Title>
                </Card.Header>
                <Card.Content className="flex flex-col gap-1.5 text-sm">
                  <Field
                    label="客単価"
                    value={
                      discussions.sales.average_customer_spend
                        ? `昼 ${discussions.sales.average_customer_spend.lunch ?? "−"}円 / 夜 ${
                            discussions.sales.average_customer_spend.dinner ?? "−"
                          }円`
                        : undefined
                    }
                  />
                  <Field
                    label="席稼働率"
                    value={
                      discussions.sales.seat_utilization
                        ? `平日 ${discussions.sales.seat_utilization.weekday ?? "−"}% / 週末 ${
                            discussions.sales.seat_utilization.weekend ?? "−"
                          }%`
                        : undefined
                    }
                  />
                  <Field label="客層" value={discussions.sales.customer_segment} />
                  <Field label="施策" value={discussions.sales.current_initiatives} />
                </Card.Content>
              </Card.Root>
            )}

            {discussions.booking_efficiency && (
              <Card.Root>
                <Card.Header>
                  <Card.Title>予約・業務効率</Card.Title>
                </Card.Header>
                <Card.Content className="flex flex-col gap-1.5 text-sm">
                  <Field
                    label="電話対応"
                    value={discussions.booking_efficiency.phone_response?.frequency}
                  />
                  <Field
                    label="発注時間"
                    value={
                      discussions.booking_efficiency.daily_ordering_time
                        ? `約${discussions.booking_efficiency.daily_ordering_time}分/日`
                        : undefined
                    }
                  />
                  <Field
                    label="発注責当"
                    value={discussions.booking_efficiency.ordering_responsible}
                  />
                </Card.Content>
              </Card.Root>
            )}

            {discussions.inbound && (
              <Card.Root>
                <Card.Header>
                  <Card.Title>インバウンド集客</Card.Title>
                </Card.Header>
                <Card.Content className="flex flex-col gap-1.5 text-sm">
                  <Field
                    label="月間外国人客"
                    value={
                      discussions.inbound.monthly_foreign_guests !== undefined
                        ? `${discussions.inbound.monthly_foreign_guests}名`
                        : undefined
                    }
                  />
                  <Field label="多言語対応" value={discussions.inbound.multilingual_support} />
                </Card.Content>
              </Card.Root>
            )}
          </div>

          <Card.Root>
            <Card.Header>
              <Card.Title>商談履歴</Card.Title>
            </Card.Header>
            <Card.Content className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
              {card.all_records.map((record, i) => (
                <div key={record.meeting_id} className="flex flex-col gap-1 py-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">
                      #{card.all_records.length - i} — {formatDate(record.company_info.date)}
                    </p>
                    <Chip size="sm">
                      <Chip.Label>{Math.round(record.confidence_score * 100)}%</Chip.Label>
                    </Chip>
                  </div>
                  <p className="text-sm text-neutral-500">
                    接触者: {record.company_info.contact_name}
                  </p>
                  {record.summary && <p className="text-sm">{record.summary}</p>}
                </div>
              ))}
            </Card.Content>
          </Card.Root>
        </>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <p>
      <span className="text-neutral-500">{label}: </span>
      <span>{value}</span>
    </p>
  );
}

function staffLine(staff?: { employees?: number; part_time?: number }): string | undefined {
  if (!staff) return undefined;
  return `社員 ${staff.employees ?? "−"}名 / パート・アルバイト ${staff.part_time ?? "−"}名`;
}
