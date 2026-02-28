export type ClaimStatus = 'CLAIM_PENDING' | 'CLAIMED' | 'CLAIM_REJECTED';

export interface ClaimVendor {
  id: string;
  business_name: string;
  area_name: string;
  phone_number: string;
  claimed_status: ClaimStatus;
  claimed_at: string | null;
  owner_id: string | null;
  owner_email: string | null;
  owner_phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimListResponse {
  success: boolean;
  data: {
    results: ClaimVendor[];
    count: number;
  };
}
