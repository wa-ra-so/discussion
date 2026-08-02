"use client";

import { useState } from "react";
import { Card } from "@heroui/react";
import { Button } from "@heroui/react";
import { TextField } from "@heroui/react";
import { Label } from "@heroui/react";
import { Input } from "@heroui/react";
import { Spinner } from "@heroui/react";
import { Alert } from "@heroui/react";
import { Chip } from "@heroui/react";
import { Search } from "lucide-react";
import { ApiRequestError, searchIssues } from "@/lib/api";
import { categoryColor, categoryLabel, formatDate } from "@/lib/constants";
import { PriorityIndicator } from "@/components/PriorityIndicator";
import { EmptyState } from "@/components/EmptyState";
import type { SearchIssueResult } from "@/lib/types";

export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchIssueResult[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (query.trim().length < 2) {
      setError("2文字以上のキーワードを入力してください");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await searchIssues({ query: query.trim(), limit: 50 });
      setResults(data.issues);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "検索に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const categoryCounts = results?.reduce<Record<string, number>>((acc, issue) => {
    acc[issue.category] = (acc[issue.category] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      <Card.Root>
        <Card.Header>
          <Card.Title>課題を検索</Card.Title>
          <Card.Description>キーワードで優先課題・カテゴリを横断検索します</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <div className="flex items-end gap-3">
            <TextField.Root
              value={query}
              onChange={setQuery}
              className="flex flex-1 flex-col gap-1.5"
            >
              <Label>検索キーワード</Label>
              <Input
                placeholder="人手不足、予約効率、インバウンド..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
              />
            </TextField.Root>
            <Button onClick={handleSearch} isDisabled={isLoading}>
              <Search className="mr-1 h-4 w-4" /> 検索
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
              <Spinner /> 検索中...
            </div>
          )}

          {!isLoading && results && (
            <>
              {categoryCounts && Object.keys(categoryCounts).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(categoryCounts).map(([category, count]) => (
                    <Chip key={category} size="sm" color={categoryColor(category)}>
                      <Chip.Label>
                        {categoryLabel(category)}: {count}件
                      </Chip.Label>
                    </Chip>
                  ))}
                </div>
              )}

              <div className="flex flex-col divide-y divide-neutral-200 dark:divide-neutral-800">
                {results.length === 0 && (
                  <EmptyState icon={Search} message="該当する課題は見つかりませんでした" />
                )}
                {results.map((issue, i) => (
                  <div key={i} className="flex flex-col gap-1 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{issue.company_name}</span>
                        {issue.corporate_name && (
                          <span className="text-xs text-neutral-500">
                            ({issue.corporate_name})
                          </span>
                        )}
                        <Chip size="sm" color={categoryColor(issue.category)}>
                          <Chip.Label>{categoryLabel(issue.category)}</Chip.Label>
                        </Chip>
                      </div>
                      <PriorityIndicator value={issue.priority} />
                    </div>
                    <p className="text-sm">{issue.issue}</p>
                    <p className="text-xs text-neutral-500">{formatDate(issue.meeting_date)}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card.Content>
      </Card.Root>
    </div>
  );
}
