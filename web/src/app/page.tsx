"use client";

import { useState } from "react";
import { Tabs } from "@heroui/react";
import { UploadCloud, ListChecks, Search, IdCard, MessageSquareText } from "lucide-react";
import { ProcessPanel } from "@/components/ProcessPanel";
import { ListPanel } from "@/components/ListPanel";
import { SearchPanel } from "@/components/SearchPanel";
import { CardPanel } from "@/components/CardPanel";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Home() {
  const [pendingSelection, setPendingSelection] = useState<{
    name: string;
    kind: "store" | "corporate";
  } | null>(null);
  const [selectedTab, setSelectedTab] = useState("process");

  const goToCard = (name: string, kind: "store" | "corporate") => {
    setPendingSelection({ name, kind });
    setSelectedTab("card");
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-8 sm:px-8 sm:py-10">
      <header className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent)] text-[var(--accent-foreground)] shadow-[var(--surface-shadow)]">
            <MessageSquareText className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="flex flex-col gap-0.5">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">商談解析システム</h1>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 sm:text-base">
              食べログ営業向け ― 商談音声を自動解析し、法人カルテとして蓄積します
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <Tabs.Root selectedKey={selectedTab} onSelectionChange={(key) => setSelectedTab(String(key))}>
        <Tabs.ListContainer>
          <Tabs.List className="flex gap-1">
            <Tabs.Tab id="process">
              <UploadCloud className="mr-1.5 h-4 w-4" /> 音声処理
            </Tabs.Tab>
            <Tabs.Tab id="list">
              <ListChecks className="mr-1.5 h-4 w-4" /> 一覧
            </Tabs.Tab>
            <Tabs.Tab id="search">
              <Search className="mr-1.5 h-4 w-4" /> 検索
            </Tabs.Tab>
            <Tabs.Tab id="card">
              <IdCard className="mr-1.5 h-4 w-4" /> 法人カルテ
            </Tabs.Tab>
          </Tabs.List>
        </Tabs.ListContainer>

        <Tabs.Panel id="process" className="animate-in fade-in slide-in-from-bottom-1 pt-6 duration-200">
          <ProcessPanel />
        </Tabs.Panel>
        <Tabs.Panel id="list" className="animate-in fade-in slide-in-from-bottom-1 pt-6 duration-200">
          <ListPanel onSelectCard={goToCard} />
        </Tabs.Panel>
        <Tabs.Panel id="search" className="animate-in fade-in slide-in-from-bottom-1 pt-6 duration-200">
          <SearchPanel />
        </Tabs.Panel>
        <Tabs.Panel id="card" className="animate-in fade-in slide-in-from-bottom-1 pt-6 duration-200">
          <CardPanel
            initialSelection={pendingSelection}
            onSelectionLoaded={() => setPendingSelection(null)}
          />
        </Tabs.Panel>
      </Tabs.Root>

      <footer className="pb-4 pt-8 text-center text-xs text-neutral-400">
        Discussion System · Powered by Whisper + Claude API
      </footer>
    </div>
  );
}
