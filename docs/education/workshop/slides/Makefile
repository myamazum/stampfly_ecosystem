# StampFly Workshop Slides — Build Automation
# Usage:
#   make all       — Build everything (tikz + main)
#   make tikz      — TikZ diagrams → PDF → PNG
#   make main      — Unified Beamer PDF (all lessons)
#   make beamer    — Individual lesson PDFs (legacy)
#   make chapter   — Single chapter: make chapter NAME=led_control
#   make clean     — Remove build artifacts

.PHONY: all tikz main beamer chapter clean

# ---------------------------------------------------------------------------
# TikZ diagrams
# ---------------------------------------------------------------------------

TIKZ_DIR   := tikz
IMAGES_DIR := images
TIKZ_DPI   := 300

TIKZ_SOURCES := $(wildcard $(TIKZ_DIR)/*.tex)
TIKZ_PDFS    := $(TIKZ_SOURCES:.tex=.pdf)
TIKZ_PNGS    := $(patsubst $(TIKZ_DIR)/%.tex,$(IMAGES_DIR)/%.png,$(TIKZ_SOURCES))

tikz: $(TIKZ_PNGS)

$(TIKZ_DIR)/%.pdf: $(TIKZ_DIR)/%.tex
	cd $(TIKZ_DIR) && lualatex -interaction=nonstopmode $(notdir $<)

$(IMAGES_DIR)/%.png: $(TIKZ_DIR)/%.pdf
	@mkdir -p $(IMAGES_DIR)
	pdftoppm -png -r $(TIKZ_DPI) -singlefile $< $(IMAGES_DIR)/$*

# ---------------------------------------------------------------------------
# Unified Beamer PDF (all lessons in one document)
# ---------------------------------------------------------------------------

BEAMER_DIR      := beamer
CHAPTER_SOURCES := $(wildcard $(BEAMER_DIR)/chapters/*.tex)

main: $(BEAMER_DIR)/main.pdf

$(BEAMER_DIR)/main.pdf: $(BEAMER_DIR)/main.tex $(BEAMER_DIR)/preamble.tex $(BEAMER_DIR)/stampfly_slides.sty $(CHAPTER_SOURCES)
	cd $(BEAMER_DIR) && lualatex -interaction=nonstopmode main.tex && lualatex -interaction=nonstopmode main.tex

# ---------------------------------------------------------------------------
# Single chapter build (for fast iteration)
# Usage: make chapter NAME=led_control
# ---------------------------------------------------------------------------

chapter:
ifndef NAME
	$(error Usage: make chapter NAME=<chapter_name> (e.g., make chapter NAME=led_control))
endif
	@echo "Building single chapter: $(NAME)"
	@cd $(BEAMER_DIR) && lualatex -interaction=nonstopmode "\documentclass[aspectratio=169,14pt]{beamer}\usepackage{stampfly_slides}\input{preamble}\title{StampFly Workshop}\author{StampFly Workshop}\date{}\begin{document}\input{chapters/$(NAME)}\end{document}"

# ---------------------------------------------------------------------------
# Individual lesson PDFs (legacy, for backward compatibility)
# ---------------------------------------------------------------------------

BEAMER_SOURCES := $(wildcard $(BEAMER_DIR)/lesson_*.tex)
BEAMER_PDFS    := $(BEAMER_SOURCES:.tex=.pdf)

beamer: $(BEAMER_PDFS)

$(BEAMER_DIR)/lesson_%.pdf: $(BEAMER_DIR)/lesson_%.tex $(BEAMER_DIR)/stampfly_slides.sty $(TIKZ_SOURCES)
	cd $(BEAMER_DIR) && lualatex -interaction=nonstopmode $(notdir $<) && lualatex -interaction=nonstopmode $(notdir $<)

# ---------------------------------------------------------------------------
# All
# ---------------------------------------------------------------------------

all: tikz main

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	rm -f $(TIKZ_DIR)/*.aux $(TIKZ_DIR)/*.log $(TIKZ_DIR)/*.pdf
	rm -f $(BEAMER_DIR)/*.aux $(BEAMER_DIR)/*.log $(BEAMER_DIR)/*.nav \
	      $(BEAMER_DIR)/*.out $(BEAMER_DIR)/*.snm $(BEAMER_DIR)/*.toc \
	      $(BEAMER_DIR)/*.vrb
	rm -f $(BEAMER_DIR)/main.pdf
	rm -f $(IMAGES_DIR)/*.png
