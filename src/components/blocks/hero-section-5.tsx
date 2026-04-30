'use client';
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { InfiniteSlider } from '@/components/ui/infinite-slider';
import { ProgressiveBlur } from '@/components/ui/progressive-blur';
import { cn } from '@/lib/utils';
import { Menu, X, ChevronRight } from 'lucide-react';
import { useScroll, motion } from 'framer-motion';
import dnaVideo from '@/dna-video.webm';
import logoDSCE from '@/Logos/logo_dsce.png';
import logoNCBI from '@/Logos/logo_ncbi.svg';
import logoBVBRC from '@/Logos/logo_bvbrc.png';
import logoDerbi from '@/Logos/logo_derbi.png';


export function HeroSection() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-background text-foreground">

            <main className="overflow-x-hidden">
                <section className="relative w-full overflow-hidden">
                    {/* Background Video */}
                    <div className="absolute inset-0 z-0">
                        <video
                            autoPlay
                            loop
                            muted
                            playsInline
                            className="h-full w-full object-cover"
                        >
                            <source src={dnaVideo} type="video/webm" />
                        </video>
                        {/* Gradient to merge video into the black slider section below */}
                        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black to-transparent pointer-events-none" />
                    </div>
                    <div className="relative z-10 py-24 md:pb-32 lg:pb-36 lg:pt-32">
                        <div className="mx-auto flex max-w-7xl flex-col px-6 lg:block lg:px-12">
                            <div className="mx-auto max-w-lg text-center lg:ml-0 lg:max-w-full lg:text-left">
                                <h1 className="mt-8 max-w-2xl text-balance text-5xl md:text-6xl lg:mt-16 xl:text-7xl font-bold tracking-tight text-white drop-shadow-sm">
                                    Predict Resistance 10x Faster
                                </h1>
                                <p className="mt-8 max-w-2xl text-balance text-lg text-white/90 drop-shadow-sm font-medium">
                                    AI-powered antimicrobial resistance prediction from whole-genome sequences.
                                    Leverage cutting-edge XGBoost and DNABERT transformer models to interpret genomic data instantly.
                                </p>

                                <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row lg:justify-start">
                                    <Button
                                        size="lg"
                                        onClick={() => navigate('/app?tab=upload')}
                                        className="h-12 rounded-full pl-6 pr-4 text-base bg-blue-600 hover:bg-blue-700 text-white shadow-lg"
                                    >
                                        <span className="text-nowrap">Start Analyzing</span>
                                        <ChevronRight className="ml-2 h-5 w-5" />
                                    </Button>
                                    <Button
                                        key={2}
                                        size="lg"
                                        variant="outline"
                                        onClick={() => navigate('/app?tab=database')}
                                        className="h-12 rounded-full px-6 text-base border-white/30 text-white hover:bg-white/10 bg-white/5 backdrop-blur-sm"
                                    >
                                        <span className="text-nowrap">Explore Database</span>
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                <section className="bg-black py-6">
                    <div className="group relative m-auto max-w-7xl px-6">
                        <div className="flex flex-col items-center md:flex-row">
                            <div className="md:w-auto md:border-r md:pr-6 md:border-white/10 mb-4 md:mb-0">
                                <p className="text-center md:text-end text-sm text-slate-500 font-medium">Compute and data resources powered by</p>
                            </div>
                            <div className="relative py-6 md:w-[calc(100%-11rem)] w-full">
                                <InfiniteSlider
                                    duration={40}
                                    gap={60}>
                                    <div className="flex items-center justify-center min-w-32 h-[3.3rem] grayscale hover:grayscale-0 transition-all duration-300 opacity-80 hover:opacity-100">
                                        <img src={logoDSCE} alt="Dayananda Sagar College of Engineering" className="h-full w-auto object-contain cursor-help" title="Dayananda Sagar College of Engineering" />
                                    </div>
                                    <div className="flex items-center justify-center min-w-32 h-[2.75rem] grayscale hover:grayscale-0 transition-all duration-300 opacity-80 hover:opacity-100">
                                        <img src={logoNCBI} alt="National Center for Biotechnology Information" className="h-full w-full object-contain cursor-help" title="National Center for Biotechnology Information" />
                                    </div>
                                    <div className="flex items-center justify-center min-w-32 h-[2.75rem] grayscale hover:grayscale-0 transition-all duration-300 opacity-80 hover:opacity-100">
                                        <img src={logoBVBRC} alt="BV-BRC" className="h-full w-auto object-contain cursor-help" title="Bacterial and Viral Bioinformatics Resource Center" />
                                    </div>
                                    <div className="flex items-center justify-center min-w-32 h-[3.3rem] grayscale hover:grayscale-0 transition-all duration-300 opacity-80 hover:opacity-100">
                                        <img src={logoDerbi} alt="DERBI Foundation" className="h-full w-auto object-contain cursor-help" title="DERBI Foundation" />
                                    </div>
                                </InfiniteSlider>

                                <div className="bg-gradient-to-r from-black to-transparent absolute inset-y-0 left-0 w-20"></div>
                                <div className="bg-gradient-to-l from-black to-transparent absolute inset-y-0 right-0 w-20"></div>
                                <ProgressiveBlur
                                    className="pointer-events-none absolute left-0 top-0 h-full w-20 opacity-50"
                                    direction="left"
                                    blurIntensity={1}
                                />
                                <ProgressiveBlur
                                    className="pointer-events-none absolute right-0 top-0 h-full w-20 opacity-50"
                                    direction="right"
                                    blurIntensity={1}
                                />
                            </div>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    )
}

