import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Contrato 1.1: a frente A escreve em src/content/docs/<slug>.md;
// a frente B define o schema exatamente assim e renderiza em /docs/<slug>/.
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const SECOES = ['comece', 'conceitos', 'fluxo', 'referencia'] as const;

const docs = defineCollection({
  loader: glob({
    pattern: '**/*.md',
    base: './src/content/docs',
    generateId: ({ entry }) => {
      const slug = entry.replace(/\.md$/, '');
      if (!SLUG.test(slug)) {
        throw new Error(
          `Arquivo "${entry}" fora do contrato 1.1: o slug deve ser minúsculas com hífen, direto em src/content/docs/.`,
        );
      }
      return slug;
    },
  }),
  schema: z
    .object({
      titulo: z.string().trim().min(1),
      descricao: z.string().trim().min(1).max(160),
      secao: z.enum(SECOES),
      ordem: z.number().int(),
      destaque: z.boolean().default(false),
    })
    .strict(),
});

export const collections = { docs };
