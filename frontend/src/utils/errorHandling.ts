import { AxiosError } from 'axios';
import { ZodError } from 'zod';

export interface ApiError {
  message: string;
  status?: number;
  details?: unknown;
}

export function handleApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    return {
      message: error.response?.data?.message || error.message,
      status: error.response?.status,
      details: error.response?.data,
    };
  }
  
  if (error instanceof ZodError) {
    return {
      message: 'Validation error',
      details: error.issues,
    };
  }
  
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }
  
  return {
    message: 'An unknown error occurred',
  };
}