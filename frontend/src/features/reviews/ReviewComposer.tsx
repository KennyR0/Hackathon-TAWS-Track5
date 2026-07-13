import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import type { ApiReviewStatus } from '../../shared/api/contracts'
import { useCreateReviewMutation } from '../../shared/api/queries'

const reviewSchema = z.object({
  status: z.enum(['reviewed', 'escalated', 'discarded']),
  justification: z.string().min(12, 'La justificacion debe explicar la decision con suficiente contexto.'),
})

type ReviewFormValues = z.infer<typeof reviewSchema>

export function ReviewComposer({ signalId, currentStatus }: { signalId: string; currentStatus: ApiReviewStatus }) {
  const mutation = useCreateReviewMutation(signalId)
  const form = useForm<ReviewFormValues>({
    resolver: zodResolver(reviewSchema),
    defaultValues: { status: 'reviewed', justification: '' },
  })

  const onSubmit = form.handleSubmit(async values => {
    mutation.reset()
    try {
      await mutation.mutateAsync(values)
      form.reset({ status: values.status, justification: '' })
    } catch {
      // The mutation state renders the API error next to the action.
    }
  })

  const savedReview = mutation.data?.data.at(-1)

  return (
    <form className="review-form" onSubmit={onSubmit}>
      <div className="toolbar-grid">
        <label className="field">
          <span>Estado nuevo</span>
          <select {...form.register('status')}>
            <option value="reviewed">Reviewed</option>
            <option value="escalated">Escalated</option>
            <option value="discarded">Discarded</option>
          </select>
        </label>
        <label className="field field--wide">
          <span>Justificacion obligatoria</span>
          <textarea rows={4} placeholder="Resume la evidencia que sostiene tu decision." {...form.register('justification')} />
        </label>
      </div>
      {form.formState.errors.justification ? <p className="field-error">{form.formState.errors.justification.message}</p> : null}
      <div className="card-actions">
        <span className="inline-hint">Estado actual: {currentStatus}</span>
        <button className="primary-button" disabled={mutation.isPending} type="submit">
          {mutation.isPending ? 'Guardando revisión' : 'Guardar decisión'}
        </button>
      </div>
      {mutation.isError ? (
        <p className="field-error" role="alert">
          {mutation.error instanceof Error ? mutation.error.message : 'No se pudo guardar la decisión.'}
        </p>
      ) : null}
      {mutation.isSuccess && savedReview ? (
        <p className="inline-hint" role="status">
          Decisión guardada en el flujo por {savedReview.reviewedBy.name}.
        </p>
      ) : null}
    </form>
  )
}
