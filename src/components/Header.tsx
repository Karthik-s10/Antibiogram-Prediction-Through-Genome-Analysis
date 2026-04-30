import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Menu, X } from 'lucide-react';
import { motion } from 'framer-motion';
import logoVanguard from '@/Logos/logo_vanguard.svg';

const menuItems = [
    { name: 'Genome Upload', href: '/app?tab=upload' },
    { name: 'Genome Database', href: '/app?tab=database' },
    { name: 'Results Dashboard', href: '/app?tab=results' },
    { name: 'Model Training', href: '/app?tab=training' },
    { name: 'Training Status', href: '/app?tab=training-status' },
];

const Logo = ({ className }: { className?: string }) => {
    return (
        <img
            src={logoVanguard}
            alt="Vanguard Logo"
            className={cn('h-14 lg:h-16 w-[180px] lg:w-[220px] object-contain object-left', className)}
        />
    )
}

export const Header = () => {
    const [menuState, setMenuState] = React.useState(false);

    return (
        <header>
            <nav
                data-state={menuState && 'active'}
                className="group fixed z-50 w-full pt-2">
                <div className={cn('mx-auto max-w-7xl rounded-3xl px-4 lg:px-8 transition-all duration-300 bg-black/40 backdrop-blur-md shadow-sm border border-white/10')}>
                    <motion.div
                        className={cn('relative flex flex-wrap items-center justify-between gap-4 py-2 duration-200 lg:gap-0 lg:py-2')}>
                        <div className="flex w-full items-center justify-between lg:w-fit lg:justify-start">
                            <Link
                                to="/"
                                className="flex items-center space-x-2">
                                <Logo className="text-white" />
                            </Link>

                            <button
                                onClick={() => setMenuState(!menuState)}
                                aria-label={menuState == true ? 'Close Menu' : 'Open Menu'}
                                className="relative z-20 -m-2.5 -mr-4 block cursor-pointer p-2.5 lg:hidden text-white">
                                <Menu className="group-data-[state=active]:rotate-180 group-data-[state=active]:scale-0 group-data-[state=active]:opacity-0 m-auto size-6 duration-200" />
                                <X className="group-data-[state=active]:rotate-0 group-data-[state=active]:scale-100 group-data-[state=active]:opacity-100 absolute inset-0 m-auto size-6 -rotate-180 scale-0 opacity-0 duration-200" />
                            </button>
                        </div>

                        <div className="hidden lg:flex lg:flex-1 lg:justify-center lg:px-4">
                            <ul className="flex flex-wrap items-center justify-center gap-4 lg:gap-6 text-sm font-mono tracking-wide">
                                {menuItems.map((item, index) => (
                                    <li key={index}>
                                        <Link
                                            to={item.href}
                                            className="transition-all duration-300 text-slate-300 hover:text-white font-normal text-base py-1">
                                            <span>{item.name}</span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="bg-slate-950/90 group-data-[state=active]:block lg:group-data-[state=active]:flex mb-6 hidden w-full flex-wrap items-center justify-end space-y-8 rounded-3xl border border-white/10 p-6 shadow-xl lg:m-0 lg:flex lg:w-fit lg:justify-end lg:gap-6 lg:space-y-0 lg:border-transparent lg:bg-transparent lg:p-0 lg:shadow-none">
                            <div className="lg:hidden">
                                <ul className="space-y-4 text-base font-mono tracking-wide text-center lg:text-left">
                                    {menuItems.map((item, index) => (
                                        <li key={index}>
                                            <Link
                                                to={item.href}
                                                onClick={() => setMenuState(false)}
                                                className="block transition-all duration-300 text-slate-300 hover:text-white font-normal text-lg py-2">
                                                <span>{item.name}</span>
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="flex w-full flex-col space-y-3 sm:flex-row sm:gap-3 sm:space-y-0 md:w-fit">
                                <Button
                                    asChild
                                    size="sm"
                                    className="bg-blue-600 hover:bg-blue-700 text-white rounded-full px-6">
                                    <Link to="/app">
                                        <span>Launch App</span>
                                    </Link>
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </nav>
        </header>
    );
}
