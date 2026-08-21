// Hook de lancement asynchrone de l'agent (file Redis/RQ).
// Gère le polling du statut du job et l'invalidation des données.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAgentJob, runAgent } from "@/api/client";
import type { AgentJob, AgentRunResult } from "@/types";

const ACTIVE = ["queued", "started"];

export function useAgentRun() {
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: (mode?: string) => runAgent(mode),
    onSuccess: (job: AgentJob) => {
      if (job.job_id && ACTIVE.includes(job.status)) {
        setJobId(job.job_id); // file asynchrone → on poll le statut
      } else {
        qc.invalidateQueries(); // repli synchrone → résultat immédiat
      }
    },
    onError: () => qc.invalidateQueries(),
  });

  const { data: job } = useQuery({
    queryKey: ["agent-job", jobId],
    queryFn: () => getAgentJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => (ACTIVE.includes(query.state.data?.status ?? "") ? 2000 : false),
  });

  useEffect(() => {
    if (job && (job.status === "finished" || job.status === "failed")) {
      setJobId(null);
      qc.invalidateQueries();
    }
  }, [job, qc]);

  const isSync = !!start.data && !start.data.job_id;
  const result: AgentRunResult | null | undefined = job?.result ?? (isSync ? start.data?.result : null);
  const error = job?.error ?? (isSync ? start.data?.error : null);
  const status = job?.status ?? (isSync ? start.data?.status : start.isPending ? "started" : null);

  // Signature explicite pour éviter l'inférence fragile de mutate() dans React Query v5
  const run = (mode?: string) => start.mutate(mode);

  return {
    start: run,
    isPending: start.isPending,
    isRunning: start.isPending || !!jobId,
    result,
    error,
    status,
  };
}
