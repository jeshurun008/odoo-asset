import { createFileRoute } from '@tanstack/react-router'
import Hero from '../components/marketing/Hero'

export const Route = createFileRoute('/')({
  component: Hero,
})