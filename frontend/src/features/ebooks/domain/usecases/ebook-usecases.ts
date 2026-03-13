import { createAsyncThunk } from '@reduxjs/toolkit'
import type { Gateways } from '../ports/gateways'
import type { CreateEbookRequest } from '../ports/ebook-gateway'

export const listEbooks = createAsyncThunk(
  'ebooks/list',
  async ({ page }: { page: number }, { extra }) => {
    const { ebookGateway } = extra as Gateways
    return ebookGateway.list(page)
  },
)

export const getEbookDetail = createAsyncThunk(
  'ebooks/getDetail',
  async (id: number, { extra }) => {
    const { ebookGateway } = extra as Gateways
    return ebookGateway.getById(id)
  },
)

export const createEbook = createAsyncThunk(
  'ebooks/create',
  async (data: CreateEbookRequest, { extra }) => {
    const { ebookGateway } = extra as Gateways
    return ebookGateway.create(data)
  },
)

export const fetchFormConfig = createAsyncThunk(
  'ebooks/fetchFormConfig',
  async (_, { extra }) => {
    const { ebookGateway } = extra as Gateways
    return ebookGateway.getFormConfig()
  },
)
