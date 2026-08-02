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
import { Building2, CalendarX, ChevronLeft, Store, Users } from "lucide-react";
import { ApiRequestError, listMeetings } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/constants";
import { EmptyState } from "@/components/EmptyState";
import type {
  CompanySummary,
  CorporationSummary,
  MeetingSummary,
  StoreIssueSummary,
} from "@/lib/types";

type View = "root" | "corporate-stores" | "store-meetings";

export function ListPanel({
  onSelectCard,
}: {
  onSelectCard: (name: string, kind: "store" | "corporate") => void;
}) {
  const [filter, setFilter] = useState("");
  const [view, setView] = useState<View>("root");
  const [corporations, setCorporations] = useState<CorporationSummary[] | null>(null);
  const [companies, setCompanies] = useState<CompanySummary[] | null>(null);
  const [corporateStores, setCorporateStores] = useState<StoreIssueSummary[] | null>(null);
  const [meetings, setMeetings] = useState<MeetingSummary[] | null>(null);
  const [activeCorporate, setActiveCorporate] = useState<string | null>(null);
  const [activeCompany, setActiveCompany] = useState<string | null>(null);
  const [cameFromCorporate, setCameFromCorporate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRoot = async () => {
    setIsLoading(true);
    setError(null);
    setView("root");
    setActiveCorporate(null);
    setActiveCompany(null);
    setCameFromCorporate(null);
    try {
      const data = await listMeetings({ limit: 50 });
      setCorporations(data.corporations ?? []);
      setCompanies(data.companies ?? []);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const loadCorporateStores = async (corporateName: string) => {
    setIsLoading(true);
    setError(null);
    setView("corporate-stores");
    setActiveCorporate(corporateName);
    setActiveCompany(null);
    try {
      const data = await listMeetings({ corporateName, limit: 50 });
      setCorporateStores(data.stores ?? []);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const loadCompanyMeetings = async (companyName: string, fromCorporate?: string | null) => {
    setIsLoading(true);
    setError(null);
    setView("store-meetings");
    setActiveCompany(companyName);
    setCameFromCorporate(fromCorporate ?? null);
    try {
      const data = await listMeetings({ companyName, limit: 50 });
      setMeetings(data.meetings ?? []);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const goBack = () => {
    if (view === "store-meetings" && cameFromCorporate) {
      loadCorporateStores(cameFromCorporate);
    } else {
      loadRoot();
    }
  };

  useEffect(() => {
    loadRoot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredCorporations =
    corporations?.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase())) ?? [];
  const filteredCompanies =
    companies?.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase())) ?? [];

  const headerDescription =
    view === "store-meetings"
      ? `${activeCompany} の商談履歴`
      : view === "corporate-stores"
        ? `${activeCorporate} の傘下店舗`
        : "登録済みの法人・店舗一覧";

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>商談記録一覧</Card.Title>
          <Card.Description>{headerDescription}</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <div className="flex items-end gap-3">
            {view === "root" ? (
              <TextField.Root
                value={filter}
                onChange={setFilter}
                className="flex flex-1 flex-col gap-1.5"
              >
                <Label>法人名・店舗名で絞り込み</Label>
                <Input placeholder="レストランA" />
              </TextField.Root>
            ) : (
              <Button variant="outline" onClick={goBack}>
                <ChevronLeft className="mr-1 h-4 w-4" />
                {view === "store-meetings" && cameFromCorporate
                  ? `${cameFromCorporate} の店舗一覧に戻る`
                  : "法人・店舗一覧に戻る"}
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

          {!isLoading && view === "root" && (
            <div className="flex flex-col gap-6">
              {filteredCorporations.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    法人
                  </p>
                  <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
                    {filteredCorporations.map((corp) => (
                      <button
                        key={corp.corporation_id}
                        onClick={() => loadCorporateStores(corp.name)}
                        className="flex cursor-pointer items-center justify-between gap-4 rounded-lg py-3 text-left transition-colors duration-150 hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)]"
                      >
                        <div className="flex items-center gap-3">
                          <Building2 className="h-5 w-5 text-[var(--accent)]" />
                          <div>
                            <p className="font-medium">{corp.name}</p>
                            <p className="text-xs text-neutral-500">
                              {corp.store_count}店舗 ／ 最終商談: {formatDate(corp.last_meeting)}
                            </p>
                          </div>
                        </div>
                        <Chip size="sm">
                          <Chip.Label>
                            <span className="inline-flex items-center gap-1">
                              <Users className="h-3 w-3" /> {corp.meeting_count}件
                            </span>
                          </Chip.Label>
                        </Chip>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                {corporations && corporations.length > 0 && (
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    店舗
                  </p>
                )}
                <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
                  {filteredCompanies.length === 0 && filteredCorporations.length === 0 && (
                    <EmptyState icon={Building2} message="該当する法人・店舗がありません" />
                  )}
                  {filteredCompanies.map((company) => (
                    <button
                      key={company.company_id}
                      onClick={() => loadCompanyMeetings(company.name)}
                      className="flex cursor-pointer items-center justify-between gap-4 rounded-lg py-3 text-left transition-colors duration-150 hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)]"
                    >
                      <div className="flex items-center gap-3">
                        <Store className="h-5 w-5 text-[var(--accent)]" />
                        <div>
                          <p className="font-medium">{company.name}</p>
                          <p className="text-xs text-neutral-500">
                            {company.corporate_name && `${company.corporate_name} ／ `}
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
              </div>
            </div>
          )}

          {!isLoading && view === "corporate-stores" && (
            <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
              {(corporateStores?.length ?? 0) === 0 && (
                <EmptyState icon={Store} message="傘下の店舗記録がありません" />
              )}
              {corporateStores?.map((store) => (
                <button
                  key={store.company_name}
                  onClick={() => loadCompanyMeetings(store.company_name, activeCorporate)}
                  className="flex cursor-pointer items-center justify-between gap-4 rounded-lg py-3 text-left transition-colors duration-150 hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)]"
                >
                  <div className="flex items-center gap-3">
                    <Store className="h-5 w-5 text-[var(--accent)]" />
                    <div>
                      <p className="font-medium">{store.company_name}</p>
                      <p className="text-xs text-neutral-500">
                        商談{store.meeting_count}件 ／ 最終: {formatDate(store.last_meeting)}
                      </p>
                    </div>
                  </div>
                  <Chip size="sm" color={store.has_issues ? "danger" : "success"}>
                    <Chip.Label>
                      {store.has_issues ? `課題 ${store.issue_count}件` : "課題なし"}
                    </Chip.Label>
                  </Chip>
                </button>
              ))}
              {activeCorporate && (
                <div className="pt-4">
                  <Button onClick={() => onSelectCard(activeCorporate, "corporate")}>
                    法人カルテを見る
                  </Button>
                </div>
              )}
            </div>
          )}

          {!isLoading && view === "store-meetings" && (
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
              {activeCompany && (
                <div className="pt-4">
                  <Button onClick={() => onSelectCard(activeCompany, "store")}>
                    店舗カルテを見る
                  </Button>
                </div>
              )}
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
