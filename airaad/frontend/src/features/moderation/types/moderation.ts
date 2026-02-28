export interface PendingReel {
  id: string;
  title: string;
  vendor_name: string;
  vendor_id: string;
  vendor_area: string;
  duration_seconds: number;
  thumbnail_url: string;
  s3_key: string;
  moderation_notes: string;
  view_count: number;
  created_at: string;
}

export interface PendingClaim {
  vendor_id: string;
  business_name: string;
  area_name: string;
  claimed_by: string | null;
  updated_at: string;
  created_at: string;
}

export interface ModerationQueue {
  pending_reels: PendingReel[];
  pending_reels_count: number;
  pending_claims: PendingClaim[];
  pending_claims_count: number;
  total_pending: number;
}

export interface ModerationQueueResponse {
  success: boolean;
  data: ModerationQueue;
}
