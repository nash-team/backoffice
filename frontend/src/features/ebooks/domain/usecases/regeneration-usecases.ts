import { createAsyncThunk } from '@reduxjs/toolkit'
import type { Gateways } from '../ports/gateways'
import type { PageType } from '../ports/regeneration-gateway'

export const fetchPageData = createAsyncThunk(
  'regeneration/fetchPageData',
  async ({ ebookId, pageIndex }: { ebookId: number; pageIndex: number }, { extra }) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.getPageData(ebookId, pageIndex)
  },
)

export const previewRegenerate = createAsyncThunk(
  'regeneration/previewRegenerate',
  async (
    { ebookId, pageIndex, customPrompt, currentImage }: { ebookId: number; pageIndex: number; customPrompt?: string; currentImage?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.previewRegenerate(ebookId, pageIndex, customPrompt, currentImage)
  },
)

export const editPage = createAsyncThunk(
  'regeneration/editPage',
  async (
    { ebookId, pageIndex, editPrompt, currentImage }: { ebookId: number; pageIndex: number; editPrompt: string; currentImage?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.editPage(ebookId, pageIndex, editPrompt, currentImage)
  },
)

export const applyEdit = createAsyncThunk(
  'regeneration/applyEdit',
  async (
    { ebookId, pageIndex, imageBase64, prompt }: { ebookId: number; pageIndex: number; imageBase64: string; prompt?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.applyEdit(ebookId, pageIndex, imageBase64, prompt)
  },
)

export const previewRegenerateCover = createAsyncThunk(
  'regeneration/previewRegenerateCover',
  async (
    { ebookId, customPrompt, currentImage }: { ebookId: number; customPrompt?: string; currentImage?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.previewRegenerateCover(ebookId, customPrompt, currentImage)
  },
)

export const editCover = createAsyncThunk(
  'regeneration/editCover',
  async (
    { ebookId, editPrompt, currentImage }: { ebookId: number; editPrompt: string; currentImage?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.editCover(ebookId, editPrompt, currentImage)
  },
)

export const applyCoverEdit = createAsyncThunk(
  'regeneration/applyCoverEdit',
  async (
    { ebookId, imageBase64, prompt }: { ebookId: number; imageBase64: string; prompt?: string },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.applyCoverEdit(ebookId, imageBase64, prompt)
  },
)

export const regeneratePages = createAsyncThunk(
  'regeneration/regeneratePages',
  async (
    { ebookId, pageType, pageIndices }: { ebookId: number; pageType: PageType; pageIndices?: number[] },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.regenerate(ebookId, pageType, pageIndices)
  },
)

export const completePages = createAsyncThunk(
  'regeneration/completePages',
  async (
    { ebookId, targetPages }: { ebookId: number; targetPages?: number },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.completePages(ebookId, targetPages)
  },
)

export const addNewPages = createAsyncThunk(
  'regeneration/addNewPages',
  async (
    { ebookId, count }: { ebookId: number; count: number },
    { extra },
  ) => {
    const { regenerationGateway } = extra as Gateways
    return regenerationGateway.addPages(ebookId, count)
  },
)
