export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      agent_run_source_snapshots: {
        Row: {
          run_id: string
          snapshot_id: string
          snapshot_kind: string
        }
        Insert: {
          run_id: string
          snapshot_id: string
          snapshot_kind: string
        }
        Update: {
          run_id?: string
          snapshot_id?: string
          snapshot_kind?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_run_source_snapshots_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "agent_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_run_steps: {
        Row: {
          created_at: string
          id: string
          node: string
          payload: Json
          run_id: string
          status: string
          step_at: string
        }
        Insert: {
          created_at?: string
          id: string
          node: string
          payload?: Json
          run_id: string
          status: string
          step_at: string
        }
        Update: {
          created_at?: string
          id?: string
          node?: string
          payload?: Json
          run_id?: string
          status?: string
          step_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_run_steps_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "agent_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_runs: {
        Row: {
          conversation_id: string | null
          created_at: string
          current_node: string
          error_code: string | null
          finished_at: string | null
          id: string
          input_hash: string
          model_name: string | null
          organization_id: string
          prompt_version: string | null
          retry_count: number
          started_at: string
          status: Database["public"]["Enums"]["analysis_status"]
        }
        Insert: {
          conversation_id?: string | null
          created_at?: string
          current_node: string
          error_code?: string | null
          finished_at?: string | null
          id: string
          input_hash: string
          model_name?: string | null
          organization_id: string
          prompt_version?: string | null
          retry_count?: number
          started_at: string
          status: Database["public"]["Enums"]["analysis_status"]
        }
        Update: {
          conversation_id?: string | null
          created_at?: string
          current_node?: string
          error_code?: string | null
          finished_at?: string | null
          id?: string
          input_hash?: string
          model_name?: string | null
          organization_id?: string
          prompt_version?: string | null
          retry_count?: number
          started_at?: string
          status?: Database["public"]["Enums"]["analysis_status"]
        }
        Relationships: [
          {
            foreignKeyName: "agent_runs_conversation_id_fkey"
            columns: ["conversation_id"]
            isOneToOne: false
            referencedRelation: "conversations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "agent_runs_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      app_users: {
        Row: {
          auth_user_id: string | null
          created_at: string
          display_name: string
          id: string
          is_active: boolean
          organization_id: string
          role: string
          updated_at: string
        }
        Insert: {
          auth_user_id?: string | null
          created_at?: string
          display_name: string
          id: string
          is_active?: boolean
          organization_id: string
          role: string
          updated_at?: string
        }
        Update: {
          auth_user_id?: string | null
          created_at?: string
          display_name?: string
          id?: string
          is_active?: boolean
          organization_id?: string
          role?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "app_users_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      articles: {
        Row: {
          content_hash: string
          created_at: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          freshness: Json
          headline: string
          id: string
          is_synthetic: boolean
          language: string
          provider: string
          provider_article_id: string
          published_at: string
          retrieved_at: string
          source_id: string
          source_snapshot_id: string
          summary: string
          url: string
          warnings: string[]
        }
        Insert: {
          content_hash: string
          created_at?: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          freshness: Json
          headline: string
          id: string
          is_synthetic?: boolean
          language: string
          provider: string
          provider_article_id: string
          published_at: string
          retrieved_at: string
          source_id: string
          source_snapshot_id: string
          summary: string
          url: string
          warnings?: string[]
        }
        Update: {
          content_hash?: string
          created_at?: string
          data_as_of?: string
          data_mode?: Database["public"]["Enums"]["data_mode"]
          freshness?: Json
          headline?: string
          id?: string
          is_synthetic?: boolean
          language?: string
          provider?: string
          provider_article_id?: string
          published_at?: string
          retrieved_at?: string
          source_id?: string
          source_snapshot_id?: string
          summary?: string
          url?: string
          warnings?: string[]
        }
        Relationships: [
          {
            foreignKeyName: "articles_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "articles_source_snapshot_id_fkey"
            columns: ["source_snapshot_id"]
            isOneToOne: false
            referencedRelation: "raw_source_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      assets: {
        Row: {
          benchmark_asset_id: string | null
          created_at: string
          currency: string
          exchange: string | null
          id: string
          instrument_type: Database["public"]["Enums"]["instrument_type"]
          name: string
          series_id: string | null
          symbol: string
        }
        Insert: {
          benchmark_asset_id?: string | null
          created_at?: string
          currency: string
          exchange?: string | null
          id: string
          instrument_type: Database["public"]["Enums"]["instrument_type"]
          name: string
          series_id?: string | null
          symbol: string
        }
        Update: {
          benchmark_asset_id?: string | null
          created_at?: string
          currency?: string
          exchange?: string | null
          id?: string
          instrument_type?: Database["public"]["Enums"]["instrument_type"]
          name?: string
          series_id?: string | null
          symbol?: string
        }
        Relationships: [
          {
            foreignKeyName: "assets_benchmark_asset_id_fkey"
            columns: ["benchmark_asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_events: {
        Row: {
          action: string
          actor_user_id: string | null
          created_at: string
          entity_id: string
          entity_type: string
          id: string
          metadata: Json
          organization_id: string | null
        }
        Insert: {
          action: string
          actor_user_id?: string | null
          created_at?: string
          entity_id: string
          entity_type: string
          id?: string
          metadata?: Json
          organization_id?: string | null
        }
        Update: {
          action?: string
          actor_user_id?: string | null
          created_at?: string
          entity_id?: string
          entity_type?: string
          id?: string
          metadata?: Json
          organization_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_events_actor_user_id_fkey"
            columns: ["actor_user_id"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "audit_events_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      briefing_signals: {
        Row: {
          briefing_id: string
          position: number
          priority: string
          reason: string
          signal_id: string
          suggested_research_actions: string[]
        }
        Insert: {
          briefing_id: string
          position?: number
          priority: string
          reason: string
          signal_id: string
          suggested_research_actions?: string[]
        }
        Update: {
          briefing_id?: string
          position?: number
          priority?: string
          reason?: string
          signal_id?: string
          suggested_research_actions?: string[]
        }
        Relationships: [
          {
            foreignKeyName: "briefing_signals_briefing_id_fkey"
            columns: ["briefing_id"]
            isOneToOne: false
            referencedRelation: "briefings"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "briefing_signals_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
        ]
      }
      briefings: {
        Row: {
          created_at: string
          discarded_count: number
          disclaimer: string
          escalated_count: number
          executive_summary: string
          id: string
          organization_id: string
          pending_review_count: number
          requires_human_review: boolean
          reviewed_count: number
          status: Database["public"]["Enums"]["briefing_status"]
          total_signals: number
          updated_at: string
          watchlist_id: string
        }
        Insert: {
          created_at?: string
          discarded_count?: number
          disclaimer: string
          escalated_count?: number
          executive_summary: string
          id: string
          organization_id: string
          pending_review_count?: number
          requires_human_review?: boolean
          reviewed_count?: number
          status: Database["public"]["Enums"]["briefing_status"]
          total_signals?: number
          updated_at?: string
          watchlist_id: string
        }
        Update: {
          created_at?: string
          discarded_count?: number
          disclaimer?: string
          escalated_count?: number
          executive_summary?: string
          id?: string
          organization_id?: string
          pending_review_count?: number
          requires_human_review?: boolean
          reviewed_count?: number
          status?: Database["public"]["Enums"]["briefing_status"]
          total_signals?: number
          updated_at?: string
          watchlist_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "briefings_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "briefings_watchlist_id_fkey"
            columns: ["watchlist_id"]
            isOneToOne: false
            referencedRelation: "watchlists"
            referencedColumns: ["id"]
          },
        ]
      }
      checkpoint_blobs: {
        Row: {
          blob: string | null
          channel: string
          checkpoint_ns: string
          thread_id: string
          type: string
          version: string
        }
        Insert: {
          blob?: string | null
          channel: string
          checkpoint_ns?: string
          thread_id: string
          type: string
          version: string
        }
        Update: {
          blob?: string | null
          channel?: string
          checkpoint_ns?: string
          thread_id?: string
          type?: string
          version?: string
        }
        Relationships: []
      }
      checkpoint_migrations: {
        Row: {
          v: number
        }
        Insert: {
          v: number
        }
        Update: {
          v?: number
        }
        Relationships: []
      }
      checkpoint_writes: {
        Row: {
          blob: string
          channel: string
          checkpoint_id: string
          checkpoint_ns: string
          idx: number
          task_id: string
          task_path: string
          thread_id: string
          type: string | null
        }
        Insert: {
          blob: string
          channel: string
          checkpoint_id: string
          checkpoint_ns?: string
          idx: number
          task_id: string
          task_path?: string
          thread_id: string
          type?: string | null
        }
        Update: {
          blob?: string
          channel?: string
          checkpoint_id?: string
          checkpoint_ns?: string
          idx?: number
          task_id?: string
          task_path?: string
          thread_id?: string
          type?: string | null
        }
        Relationships: []
      }
      checkpoints: {
        Row: {
          checkpoint: Json
          checkpoint_id: string
          checkpoint_ns: string
          metadata: Json
          parent_checkpoint_id: string | null
          thread_id: string
          type: string | null
        }
        Insert: {
          checkpoint: Json
          checkpoint_id: string
          checkpoint_ns?: string
          metadata?: Json
          parent_checkpoint_id?: string | null
          thread_id: string
          type?: string | null
        }
        Update: {
          checkpoint?: Json
          checkpoint_id?: string
          checkpoint_ns?: string
          metadata?: Json
          parent_checkpoint_id?: string | null
          thread_id?: string
          type?: string | null
        }
        Relationships: []
      }
      claim_evidence_links: {
        Row: {
          claim_id: string
          evidence_id: string
          supports_claim: boolean
        }
        Insert: {
          claim_id: string
          evidence_id: string
          supports_claim: boolean
        }
        Update: {
          claim_id?: string
          evidence_id?: string
          supports_claim?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "claim_evidence_links_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "claim_evidence_links_evidence_id_fkey"
            columns: ["evidence_id"]
            isOneToOne: false
            referencedRelation: "evidence"
            referencedColumns: ["id"]
          },
        ]
      }
      claims: {
        Row: {
          claim: string
          claim_type: string
          created_at: string
          event_id: string
          id: string
          numeric_value: number | null
          signal_id: string
          unit: string | null
        }
        Insert: {
          claim: string
          claim_type: string
          created_at?: string
          event_id: string
          id: string
          numeric_value?: number | null
          signal_id: string
          unit?: string | null
        }
        Update: {
          claim?: string
          claim_type?: string
          created_at?: string
          event_id?: string
          id?: string
          numeric_value?: number | null
          signal_id?: string
          unit?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "claims_event_id_fkey"
            columns: ["event_id"]
            isOneToOne: false
            referencedRelation: "events"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "claims_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
        ]
      }
      conversation_messages: {
        Row: {
          content: string
          conversation_id: string
          created_at: string
          id: string
          metadata: Json
          role: string
        }
        Insert: {
          content: string
          conversation_id: string
          created_at?: string
          id: string
          metadata?: Json
          role: string
        }
        Update: {
          content?: string
          conversation_id?: string
          created_at?: string
          id?: string
          metadata?: Json
          role?: string
        }
        Relationships: [
          {
            foreignKeyName: "conversation_messages_conversation_id_fkey"
            columns: ["conversation_id"]
            isOneToOne: false
            referencedRelation: "conversations"
            referencedColumns: ["id"]
          },
        ]
      }
      conversations: {
        Row: {
          active_event_id: string | null
          active_instrument_symbol: string | null
          active_signal_id: string | null
          created_at: string
          id: string
          last_run_id: string | null
          openai_conversation_id: string | null
          organization_id: string
          summary: string | null
          updated_at: string
          user_id: string
          watchlist_id: string | null
        }
        Insert: {
          active_event_id?: string | null
          active_instrument_symbol?: string | null
          active_signal_id?: string | null
          created_at?: string
          id: string
          last_run_id?: string | null
          openai_conversation_id?: string | null
          organization_id: string
          summary?: string | null
          updated_at?: string
          user_id: string
          watchlist_id?: string | null
        }
        Update: {
          active_event_id?: string | null
          active_instrument_symbol?: string | null
          active_signal_id?: string | null
          created_at?: string
          id?: string
          last_run_id?: string | null
          openai_conversation_id?: string | null
          organization_id?: string
          summary?: string | null
          updated_at?: string
          user_id?: string
          watchlist_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "conversations_active_event_id_fkey"
            columns: ["active_event_id"]
            isOneToOne: false
            referencedRelation: "events"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "conversations_active_signal_id_fkey"
            columns: ["active_signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "conversations_last_run_id_fkey"
            columns: ["last_run_id"]
            isOneToOne: false
            referencedRelation: "agent_runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "conversations_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "conversations_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "conversations_watchlist_id_fkey"
            columns: ["watchlist_id"]
            isOneToOne: false
            referencedRelation: "watchlists"
            referencedColumns: ["id"]
          },
        ]
      }
      event_articles: {
        Row: {
          article_id: string
          event_id: string
          position: number
        }
        Insert: {
          article_id: string
          event_id: string
          position?: number
        }
        Update: {
          article_id?: string
          event_id?: string
          position?: number
        }
        Relationships: [
          {
            foreignKeyName: "event_articles_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "event_articles_event_id_fkey"
            columns: ["event_id"]
            isOneToOne: false
            referencedRelation: "events"
            referencedColumns: ["id"]
          },
        ]
      }
      event_asset_relations: {
        Row: {
          asset_id: string
          entity_match_score: number
          event_id: string
          reason: string
          relationship: string
        }
        Insert: {
          asset_id: string
          entity_match_score: number
          event_id: string
          reason: string
          relationship: string
        }
        Update: {
          asset_id?: string
          entity_match_score?: number
          event_id?: string
          reason?: string
          relationship?: string
        }
        Relationships: [
          {
            foreignKeyName: "event_asset_relations_asset_id_fkey"
            columns: ["asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "event_asset_relations_event_id_fkey"
            columns: ["event_id"]
            isOneToOne: false
            referencedRelation: "events"
            referencedColumns: ["id"]
          },
        ]
      }
      events: {
        Row: {
          created_at: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          event_at: string
          freshness: Json
          id: string
          organization_id: string
          provider: string
          retrieved_at: string
          summary: string
          title: string
          updated_at: string
          warnings: string[]
        }
        Insert: {
          created_at?: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          event_at: string
          freshness: Json
          id: string
          organization_id: string
          provider: string
          retrieved_at: string
          summary: string
          title: string
          updated_at?: string
          warnings?: string[]
        }
        Update: {
          created_at?: string
          data_as_of?: string
          data_mode?: Database["public"]["Enums"]["data_mode"]
          event_at?: string
          freshness?: Json
          id?: string
          organization_id?: string
          provider?: string
          retrieved_at?: string
          summary?: string
          title?: string
          updated_at?: string
          warnings?: string[]
        }
        Relationships: [
          {
            foreignKeyName: "events_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      evidence: {
        Row: {
          article_id: string | null
          claim: string
          claim_id: string
          content_hash: string
          created_at: string
          data_as_of: string
          evidence_type: string
          excerpt: string | null
          id: string
          published_at: string | null
          retrieved_at: string
          signal_id: string
          source_id: string | null
          source_snapshot_id: string | null
          source_url: string
          supports_signal: boolean
        }
        Insert: {
          article_id?: string | null
          claim: string
          claim_id: string
          content_hash: string
          created_at?: string
          data_as_of: string
          evidence_type: string
          excerpt?: string | null
          id: string
          published_at?: string | null
          retrieved_at: string
          signal_id: string
          source_id?: string | null
          source_snapshot_id?: string | null
          source_url: string
          supports_signal: boolean
        }
        Update: {
          article_id?: string | null
          claim?: string
          claim_id?: string
          content_hash?: string
          created_at?: string
          data_as_of?: string
          evidence_type?: string
          excerpt?: string | null
          id?: string
          published_at?: string | null
          retrieved_at?: string
          signal_id?: string
          source_id?: string | null
          source_snapshot_id?: string | null
          source_url?: string
          supports_signal?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "evidence_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_source_snapshot_id_fkey"
            columns: ["source_snapshot_id"]
            isOneToOne: false
            referencedRelation: "raw_source_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      evidence_market_snapshots: {
        Row: {
          evidence_id: string
          market_snapshot_id: string
        }
        Insert: {
          evidence_id: string
          market_snapshot_id: string
        }
        Update: {
          evidence_id?: string
          market_snapshot_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "evidence_market_snapshots_evidence_id_fkey"
            columns: ["evidence_id"]
            isOneToOne: false
            referencedRelation: "evidence"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_market_snapshots_market_snapshot_id_fkey"
            columns: ["market_snapshot_id"]
            isOneToOne: false
            referencedRelation: "market_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      idempotency_keys: {
        Row: {
          created_at: string
          expires_at: string
          id: string
          idempotency_key: string
          operation: string
          organization_id: string
          request_hash: string
          response_body: Json | null
          response_status: number | null
        }
        Insert: {
          created_at?: string
          expires_at: string
          id?: string
          idempotency_key: string
          operation: string
          organization_id: string
          request_hash: string
          response_body?: Json | null
          response_status?: number | null
        }
        Update: {
          created_at?: string
          expires_at?: string
          id?: string
          idempotency_key?: string
          operation?: string
          organization_id?: string
          request_hash?: string
          response_body?: Json | null
          response_status?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "idempotency_keys_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      institutional_datasets: {
        Row: {
          created_at: string
          data_as_of: string
          file_hash: string
          id: string
          institution: string
          is_live_data: boolean
          metadata: Json
          name: string
          published_at: string | null
          retrieved_at: string
          source_url: string
          storage_path: string | null
        }
        Insert: {
          created_at?: string
          data_as_of: string
          file_hash: string
          id: string
          institution: string
          is_live_data?: boolean
          metadata?: Json
          name: string
          published_at?: string | null
          retrieved_at: string
          source_url: string
          storage_path?: string | null
        }
        Update: {
          created_at?: string
          data_as_of?: string
          file_hash?: string
          id?: string
          institution?: string
          is_live_data?: boolean
          metadata?: Json
          name?: string
          published_at?: string | null
          retrieved_at?: string
          source_url?: string
          storage_path?: string | null
        }
        Relationships: []
      }
      market_observations: {
        Row: {
          close_value: number
          high_value: number | null
          low_value: number | null
          market_snapshot_id: string
          observed_at: string
          open_value: number | null
          volume: number | null
        }
        Insert: {
          close_value: number
          high_value?: number | null
          low_value?: number | null
          market_snapshot_id: string
          observed_at: string
          open_value?: number | null
          volume?: number | null
        }
        Update: {
          close_value?: number
          high_value?: number | null
          low_value?: number | null
          market_snapshot_id?: string
          observed_at?: string
          open_value?: number | null
          volume?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "market_observations_market_snapshot_id_fkey"
            columns: ["market_snapshot_id"]
            isOneToOne: false
            referencedRelation: "market_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      market_snapshots: {
        Row: {
          asset_id: string
          benchmark_asset_id: string | null
          content_hash: string
          created_at: string
          currency: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          end_at: string
          freshness: Json
          id: string
          interval: string
          missing_value_policy: string
          provider: string
          retrieved_at: string
          series_id: string | null
          source_url: string
          start_at: string
          timezone: string
          warnings: string[]
        }
        Insert: {
          asset_id: string
          benchmark_asset_id?: string | null
          content_hash: string
          created_at?: string
          currency: string
          data_as_of: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          end_at: string
          freshness: Json
          id: string
          interval: string
          missing_value_policy: string
          provider: string
          retrieved_at: string
          series_id?: string | null
          source_url: string
          start_at: string
          timezone: string
          warnings?: string[]
        }
        Update: {
          asset_id?: string
          benchmark_asset_id?: string | null
          content_hash?: string
          created_at?: string
          currency?: string
          data_as_of?: string
          data_mode?: Database["public"]["Enums"]["data_mode"]
          end_at?: string
          freshness?: Json
          id?: string
          interval?: string
          missing_value_policy?: string
          provider?: string
          retrieved_at?: string
          series_id?: string | null
          source_url?: string
          start_at?: string
          timezone?: string
          warnings?: string[]
        }
        Relationships: [
          {
            foreignKeyName: "market_snapshots_asset_id_fkey"
            columns: ["asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "market_snapshots_benchmark_asset_id_fkey"
            columns: ["benchmark_asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
        ]
      }
      organizations: {
        Row: {
          created_at: string
          id: string
          name: string
        }
        Insert: {
          created_at?: string
          id: string
          name: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
        }
        Relationships: []
      }
      provider_budgets: {
        Row: {
          max_requests: number
          period_type: string
          provider: string
          reset_at: string
          safety_reserve: number
          updated_at: string
          used_requests: number
        }
        Insert: {
          max_requests: number
          period_type: string
          provider: string
          reset_at: string
          safety_reserve?: number
          updated_at?: string
          used_requests?: number
        }
        Update: {
          max_requests?: number
          period_type?: string
          provider?: string
          reset_at?: string
          safety_reserve?: number
          updated_at?: string
          used_requests?: number
        }
        Relationships: []
      }
      provider_cache: {
        Row: {
          cache_key: string
          content_hash: string | null
          created_at: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          expires_at: string
          fetched_at: string
          id: string
          provider: string
          request_cost: number
          request_params_hash: string
          response_json: Json
          status_code: number
        }
        Insert: {
          cache_key: string
          content_hash?: string | null
          created_at?: string
          data_mode: Database["public"]["Enums"]["data_mode"]
          expires_at: string
          fetched_at?: string
          id?: string
          provider: string
          request_cost?: number
          request_params_hash: string
          response_json: Json
          status_code: number
        }
        Update: {
          cache_key?: string
          content_hash?: string | null
          created_at?: string
          data_mode?: Database["public"]["Enums"]["data_mode"]
          expires_at?: string
          fetched_at?: string
          id?: string
          provider?: string
          request_cost?: number
          request_params_hash?: string
          response_json?: Json
          status_code?: number
        }
        Relationships: []
      }
      provider_health: {
        Row: {
          circuit_state: string
          consecutive_failures: number
          last_error_code: string | null
          last_error_message: string | null
          last_failure_at: string | null
          last_success_at: string | null
          opened_at: string | null
          provider: string
          retry_after: string | null
          updated_at: string
        }
        Insert: {
          circuit_state?: string
          consecutive_failures?: number
          last_error_code?: string | null
          last_error_message?: string | null
          last_failure_at?: string | null
          last_success_at?: string | null
          opened_at?: string | null
          provider: string
          retry_after?: string | null
          updated_at?: string
        }
        Update: {
          circuit_state?: string
          consecutive_failures?: number
          last_error_code?: string | null
          last_error_message?: string | null
          last_failure_at?: string | null
          last_success_at?: string | null
          opened_at?: string | null
          provider?: string
          retry_after?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      raw_source_snapshots: {
        Row: {
          captured_at: string
          content_hash: string
          created_at: string
          id: string
          payload: Json
          provider: string
          provider_article_id: string
          source_id: string
        }
        Insert: {
          captured_at: string
          content_hash: string
          created_at?: string
          id: string
          payload: Json
          provider: string
          provider_article_id: string
          source_id: string
        }
        Update: {
          captured_at?: string
          content_hash?: string
          created_at?: string
          id?: string
          payload?: Json
          provider?: string
          provider_article_id?: string
          source_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "raw_source_snapshots_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_evidence_links: {
        Row: {
          evidence_id: string
          signal_id: string
          supports_signal: boolean
        }
        Insert: {
          evidence_id: string
          signal_id: string
          supports_signal: boolean
        }
        Update: {
          evidence_id?: string
          signal_id?: string
          supports_signal?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "signal_evidence_links_evidence_id_fkey"
            columns: ["evidence_id"]
            isOneToOne: false
            referencedRelation: "evidence"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_evidence_links_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_reviews: {
        Row: {
          created_at: string
          id: string
          justification: string
          previous_status: Database["public"]["Enums"]["review_status"]
          reviewed_at: string
          reviewed_by: string
          signal_id: string
          status: Database["public"]["Enums"]["review_status"]
        }
        Insert: {
          created_at?: string
          id: string
          justification: string
          previous_status: Database["public"]["Enums"]["review_status"]
          reviewed_at?: string
          reviewed_by: string
          signal_id: string
          status: Database["public"]["Enums"]["review_status"]
        }
        Update: {
          created_at?: string
          id?: string
          justification?: string
          previous_status?: Database["public"]["Enums"]["review_status"]
          reviewed_at?: string
          reviewed_by?: string
          signal_id?: string
          status?: Database["public"]["Enums"]["review_status"]
        }
        Relationships: [
          {
            foreignKeyName: "signal_reviews_reviewed_by_fkey"
            columns: ["reviewed_by"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_reviews_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "signals"
            referencedColumns: ["id"]
          },
        ]
      }
      signals: {
        Row: {
          abnormal_return: number | null
          analysis_status: Database["public"]["Enums"]["analysis_status"]
          asset_id: string
          asset_return: number | null
          assumptions: string[]
          benchmark_return: number | null
          confidence: number
          created_at: string
          current_review_justification: string | null
          current_review_status: Database["public"]["Enums"]["review_status"]
          current_reviewed_at: string | null
          current_reviewed_by: string | null
          disclaimer: string
          event_id: string
          historical_volatility: number | null
          id: string
          impact: Database["public"]["Enums"]["impact_status"]
          invalidation_conditions: string[]
          relative_volume: number | null
          requires_human_review: boolean
          suggested_research_actions: string[]
          thesis: string | null
          time_horizon: string
          updated_at: string
        }
        Insert: {
          abnormal_return?: number | null
          analysis_status: Database["public"]["Enums"]["analysis_status"]
          asset_id: string
          asset_return?: number | null
          assumptions?: string[]
          benchmark_return?: number | null
          confidence: number
          created_at?: string
          current_review_justification?: string | null
          current_review_status?: Database["public"]["Enums"]["review_status"]
          current_reviewed_at?: string | null
          current_reviewed_by?: string | null
          disclaimer: string
          event_id: string
          historical_volatility?: number | null
          id: string
          impact: Database["public"]["Enums"]["impact_status"]
          invalidation_conditions?: string[]
          relative_volume?: number | null
          requires_human_review?: boolean
          suggested_research_actions?: string[]
          thesis?: string | null
          time_horizon: string
          updated_at?: string
        }
        Update: {
          abnormal_return?: number | null
          analysis_status?: Database["public"]["Enums"]["analysis_status"]
          asset_id?: string
          asset_return?: number | null
          assumptions?: string[]
          benchmark_return?: number | null
          confidence?: number
          created_at?: string
          current_review_justification?: string | null
          current_review_status?: Database["public"]["Enums"]["review_status"]
          current_reviewed_at?: string | null
          current_reviewed_by?: string | null
          disclaimer?: string
          event_id?: string
          historical_volatility?: number | null
          id?: string
          impact?: Database["public"]["Enums"]["impact_status"]
          invalidation_conditions?: string[]
          relative_volume?: number | null
          requires_human_review?: boolean
          suggested_research_actions?: string[]
          thesis?: string | null
          time_horizon?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "signals_asset_id_fkey"
            columns: ["asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signals_current_reviewed_by_fkey"
            columns: ["current_reviewed_by"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signals_event_id_fkey"
            columns: ["event_id"]
            isOneToOne: false
            referencedRelation: "events"
            referencedColumns: ["id"]
          },
        ]
      }
      sources: {
        Row: {
          country_code: string
          created_at: string
          domain: string
          fixture_only: boolean
          homepage_url: string
          id: string
          is_aggregator: boolean
          is_original_publisher: boolean
          language: string
          name: string
          publisher_group_id: string
          tier: Database["public"]["Enums"]["source_tier"]
        }
        Insert: {
          country_code: string
          created_at?: string
          domain: string
          fixture_only?: boolean
          homepage_url: string
          id: string
          is_aggregator: boolean
          is_original_publisher: boolean
          language: string
          name: string
          publisher_group_id: string
          tier: Database["public"]["Enums"]["source_tier"]
        }
        Update: {
          country_code?: string
          created_at?: string
          domain?: string
          fixture_only?: boolean
          homepage_url?: string
          id?: string
          is_aggregator?: boolean
          is_original_publisher?: boolean
          language?: string
          name?: string
          publisher_group_id?: string
          tier?: Database["public"]["Enums"]["source_tier"]
        }
        Relationships: []
      }
      watchlist_assets: {
        Row: {
          asset_id: string
          created_at: string
          position: number
          watchlist_id: string
        }
        Insert: {
          asset_id: string
          created_at?: string
          position?: number
          watchlist_id: string
        }
        Update: {
          asset_id?: string
          created_at?: string
          position?: number
          watchlist_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "watchlist_assets_asset_id_fkey"
            columns: ["asset_id"]
            isOneToOne: false
            referencedRelation: "assets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "watchlist_assets_watchlist_id_fkey"
            columns: ["watchlist_id"]
            isOneToOne: false
            referencedRelation: "watchlists"
            referencedColumns: ["id"]
          },
        ]
      }
      watchlists: {
        Row: {
          created_at: string
          id: string
          name: string
          organization_id: string
        }
        Insert: {
          created_at?: string
          id: string
          name: string
          organization_id: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          organization_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "watchlists_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      analysis_status:
        | "processing"
        | "completed"
        | "insufficient_evidence"
        | "failed"
      briefing_status: "draft" | "shareable"
      data_mode: "fixture" | "live" | "fallback"
      impact_status: "positive" | "negative" | "neutral" | "uncertain"
      instrument_type:
        | "equity"
        | "etf"
        | "crypto"
        | "commodity"
        | "macro"
        | "credit"
        | "other"
      review_status: "pending_review" | "reviewed" | "escalated" | "discarded"
      source_tier: "A" | "B" | "C" | "D"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      analysis_status: [
        "processing",
        "completed",
        "insufficient_evidence",
        "failed",
      ],
      briefing_status: ["draft", "shareable"],
      data_mode: ["fixture", "live", "fallback"],
      impact_status: ["positive", "negative", "neutral", "uncertain"],
      instrument_type: [
        "equity",
        "etf",
        "crypto",
        "commodity",
        "macro",
        "credit",
        "other",
      ],
      review_status: ["pending_review", "reviewed", "escalated", "discarded"],
      source_tier: ["A", "B", "C", "D"],
    },
  },
} as const
